import os
import json
import uuid
import time
import threading
import requests
import websocket
import logging

from dotenv import load_dotenv

load_dotenv()

JEG_AUTH_TOKEN = os.getenv("JEG_AUTH_TOKEN", "jeg-jeg-an")
JEG_HOST = os.getenv("JEG_HOST_IP", "127.0.0.1")
JEG_PORT = os.getenv("JEG_PORT", "8889")

JEG_BASE_URL = f"http://{JEG_HOST}:{JEG_PORT}"
JEG_WS_URL = f"ws://{JEG_HOST}:{JEG_PORT}"

KERNEL_SPECS_TO_USE = [
    "python3-docker-rpl",
    "python3-docker-rpl-02",
    "python3-docker-rpl-1"
]

headers = {
    "Authorization": f"token {JEG_AUTH_TOKEN}",
    "Content-Type": "application/json"
}

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger("MultiKernelRunner")

active_kernels = []
kernel_results = {}

def execute_code_in_kernel(kernel_id, ws_connection, code_to_execute, kernel_name):
    logger.info(f"[{kernel_name}] Sending code to kernel {kernel_id}...")

    msg = {
        "header": {
            "msg_id": str(uuid.uuid4()),
            "username": "jovyan",
            "session": str(uuid.uuid4()),
            "msg_type": "execute_request",
            "version": "5.3"
        },
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code_to_execute,
            "silent": False
        }
    }

    output_buffer = []
    try:
        ws_connection.send(json.dumps(msg))
        timeout_start = time.time()
        timeout_seconds = 180

        while time.time() - timeout_start < timeout_seconds:
            res = json.loads(ws_connection.recv())
            msg_type = res.get("msg_type")

            if msg_type in ["stream", "execute_result"]:
                output_part = res["content"].get("text", "")
                output_buffer.append(output_part)
                logger.info(f"[{kernel_name}] Output: {output_part.strip()}")
            elif msg_type == "error":
                error_msg = f"Error: {res['content'].get('ename', '')}: {res['content'].get('evalue', '')}"
                output_buffer.append(error_msg)
                logger.error(f"[{kernel_name}] {error_msg}")
                kernel_results[kernel_id] = {
                    "status": "error",
                    "output": "".join(output_buffer),
                    "error": error_msg
                }
                return
            elif msg_type == "status" and res["content"].get("execution_state") == "idle":
                logger.info(f"[{kernel_name}] Execution finished.")
                kernel_results[kernel_id] = {
                    "status": "success",
                    "output": "".join(output_buffer)
                }
                return

        logger.warning(f"[{kernel_name}] Kernel execution timed out.")
        kernel_results[kernel_id] = {
            "status": "timeout",
            "output": "".join(output_buffer)
        }

    except websocket.WebSocketTimeoutException:
        logger.warning(f"[{kernel_name}] WebSocket recv timeout.")
        kernel_results[kernel_id] = {
            "status": "ws_timeout",
            "output": "".join(output_buffer)
        }
    except Exception as e:
        logger.exception(f"[{kernel_name}] WebSocket error.")
        kernel_results[kernel_id] = {
            "status": "exception",
            "output": "".join(output_buffer),
            "exception": str(e)
        }

"""
Main function, submit jobs to JEG kernel
"""
def main():
    logger.info("Starting multi-kernel execution...")

    code_to_run = """
import numpy as np
import time
import os

print("Starting computation")
MATRIX_SIZE = 10000
A = np.random.rand(MATRIX_SIZE, MATRIX_SIZE)
B = np.random.rand(MATRIX_SIZE, MATRIX_SIZE)

results = []
start = time.time()
duration = 0
i = 0
while duration < 60:
    C = np.matmul(A, B)
    results.append(C)
    i += 1
    duration = time.time() - start
    print(f"Iteration {i} done, elapsed time: {duration:.2f}")

print(f"Total matrices stored: {len(results)}")
print(f"Running on hostname: {os.uname().nodename}")
"""

    # Kernel creation and WebSocket setup
    for kernelspec_name in KERNEL_SPECS_TO_USE:
        try:
            logger.info(f"Creating kernel '{kernelspec_name}'...")
            resp = requests.post(f"{JEG_BASE_URL}/api/kernels", headers=headers, json={"name": kernelspec_name})
            resp.raise_for_status()

            kernel_id = resp.json()["id"]
            logger.info(f"Kernel '{kernelspec_name}' created with ID: {kernel_id}")

            ws_url = f"{JEG_WS_URL}/api/kernels/{kernel_id}/channels"
            ws_headers = [
                f"Authorization: token {JEG_AUTH_TOKEN}",
                f"Origin: http://{JEG_HOST}"
            ]
            ws_connection = websocket.create_connection(ws_url, header=ws_headers, timeout=10)
            logger.info(f"WebSocket connected to kernel {kernel_id}.")

            active_kernels.append({
                "id": kernel_id,
                "ws": ws_connection,
                "name": kernelspec_name
            })
            kernel_results[kernel_id] = {"status": "connected", "output": ""}

        except Exception as e:
            logger.error(f"Failed to initialize kernel '{kernelspec_name}': {e}")

    if not active_kernels:
        logger.error("No active kernels available. Aborting.")
        return

    # Run code in all active kernels
    logger.info("Executing code on all active kernels...")
    threads = []
    for kernel_info in active_kernels:
        t = threading.Thread(target=execute_code_in_kernel, args=(
            kernel_info["id"],
            kernel_info["ws"],
            code_to_run,
            kernel_info["name"]
        ))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Cleanup
    logger.info("Cleaning up all kernels...")
    for kernel_info in active_kernels:
        kernel_id = kernel_info["id"]
        kernel_name = kernel_info["name"]
        try:
            if kernel_info["ws"].connected:
                kernel_info["ws"].close()
                logger.info(f"WebSocket for kernel '{kernel_name}' closed.")
            requests.delete(f"{JEG_BASE_URL}/api/kernels/{kernel_id}", headers=headers)
            logger.info(f"Kernel '{kernel_name}' deleted.")
        except Exception as e:
            logger.warning(f"Failed to clean up kernel '{kernel_name}': {e}")

    # Execution Summary
    logger.info("\n========= SUMMARY :) =========")
    for kernel_id, result in kernel_results.items():
        logger.info(f"Kernel ID: {kernel_id}")
        logger.info(f"  Status : {result.get('status', 'unknown')}")
        if result.get("output"):
            logger.info(f"  Output (first 100 chars): {result['output'].strip()[:100]}...")
        if result.get("error"):
            logger.error(f"  Error: {result['error']}")
        if result.get("exception"):
            logger.error(f"  Exception: {result['exception']}")
        logger.info("-" * 40)

    logger.info("All tasks completed.")

if __name__ == "__main__":
    main()
