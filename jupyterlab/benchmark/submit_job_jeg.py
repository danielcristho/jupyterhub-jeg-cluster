import json
import uuid
import time
import websocket
import requests
import os
import threading

# Config
JEG_AUTH_TOKEN = os.environ.get("JEG_AUTH_TOKEN", "jeg-jeg-an")
JEG_HOST = os.environ.get("JEG_HOST_IP", "10.33.17.30")
JEG_PORT = os.environ.get("JEG_PORT", "8889")
JEG_BASE_URL = f"http://{JEG_HOST}:{JEG_PORT}"
JEG_WS_URL = f"ws://{JEG_HOST}:{JEG_PORT}"

headers = {
    "Authorization": f"token {JEG_AUTH_TOKEN}",
    "Content-Type": "application/json"
}

KERNEL_SPECS_TO_USE = [
    "python3-docker-rpl",
    "python3-docker-rpl-02",
    "python3-docker-rpl-1"
]

active_kernels = []
kernel_results = {}

def execute_code_in_kernel(kernel_id, ws_connection, code_to_execute, kernel_name):
    print(f"[{kernel_name}] Mengirim kode ke kernel {kernel_id}...")
    
    msg = {
        "header": {
            "msg_id": str(uuid.uuid4()),
            "username": "test_multi",
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
                print(f"[{kernel_name}] Output: {output_part.strip()}")
            elif msg_type == "error":
                error_msg = f"Error: {res['content'].get('ename', '')}: {res['content'].get('evalue', '')}"
                output_buffer.append(error_msg)
                print(f"[{kernel_name}] {error_msg}")
                kernel_results[kernel_id] = {"status": "error", "output": "".join(output_buffer), "error": error_msg}
                return
            elif msg_type == "status" and res["content"].get("execution_state") == "idle":
                print(f"[{kernel_name}] Eksekusi selesai. Output akhir: {''.join(output_buffer).strip()[:200]}...")
                kernel_results[kernel_id] = {"status": "success", "output": "".join(output_buffer)}
                return
        
        print(f"[{kernel_name}] Timeout eksekusi untuk kernel {kernel_id}.")
        kernel_results[kernel_id] = {"status": "timeout", "output": "".join(output_buffer)}

    except websocket.WebSocketTimeoutException:
        print(f"[{kernel_name}] WebSocket recv timeout for kernel {kernel_id}.")
        kernel_results[kernel_id] = {"status": "ws_timeout", "output": "".join(output_buffer)}
    except Exception as e:
        print(f"[{kernel_name}] WebSocket error for kernel {kernel_id}: {e}")
        kernel_results[kernel_id] = {"status": "exception", "output": "".join(output_buffer), "exception": str(e)}

def main():
    print("run multi-kernel jobs...")

    code_to_run = """
import numpy as np
import time
import os
import platform

print("Starting largest computation")
MATRIX_SIZE = 10000 
A = np.random.rand(MATRIX_SIZE, MATRIX_SIZE) 
B = np.random.rand(MATRIX_SIZE, MATRIX_SIZE)
start = time.time()
C = np.matmul(A, B)
end = time.time()
print("Done. Overload execution time: {:.2f} seconds".format(end - start))
print(f"Overload kernel hostname: {os.uname().nodename}")
print(f"Overload kernel platform: {platform.platform()}")
time.sleep(20) 
"""

    threads = []
    for kernelspec_name in KERNEL_SPECS_TO_USE:
        try:
            print(f"Mencoba membuat kernel: {kernelspec_name}")
            resp = requests.post(f"{JEG_BASE_URL}/api/kernels", headers=headers, json={"name": kernelspec_name})
            resp.raise_for_status()
            kernel_id = resp.json()["id"]
            print(f"Kernel '{kernelspec_name}' created with ID: {kernel_id}")

            ws_url = f"{JEG_WS_URL}/api/kernels/{kernel_id}/channels"
            ws_headers = [
                f"Authorization: token {JEG_AUTH_TOKEN}",
                f"Origin: http://{JEG_HOST}"
            ]
            ws_connection = websocket.create_connection(ws_url, header=ws_headers, timeout=10) # Timeout koneksi WS
            print(f"WebSocket terhubung ke kernel {kernel_id}.")
            
            active_kernels.append({"id": kernel_id, "ws": ws_connection, "name": kernelspec_name})
            kernel_results[kernel_id] = {"status": "connecting", "output": ""} # Inisialisasi status

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Gagal membuat kernel {kernelspec_name} via HTTP: {e}")
            continue
        except websocket.WebSocketException as e:
            print(f"ERROR: Gagal terhubung WebSocket ke kernel {kernelspec_name}: {e}")
            continue
        except Exception as e:
            print(f"ERROR: Terjadi kesalahan tak terduga saat membuat kernel {kernelspec_name}: {e}")
            continue

    if not active_kernels:
        print("Tidak ada kernel yang berhasil dibuat atau dihubungkan. Keluar.")
        return

    print("\nMenjalankan kode di semua kernel yang aktif...")
    execution_threads = []
    for kernel_info in active_kernels:
        thread = threading.Thread(target=execute_code_in_kernel, 
                                    args=(kernel_info["id"], kernel_info["ws"], code_to_run, kernel_info["name"]))
        execution_threads.append(thread)
        thread.start()

    for thread in execution_threads:
        thread.join()

    print("\nCleanup kernel...")
    for kernel_info in active_kernels:
        kernel_id = kernel_info["id"]
        ws_connection = kernel_info["ws"]
        kernel_name = kernel_info["name"]

        try:
            if ws_connection and ws_connection.connected:
                ws_connection.close()
                print(f"WebSocket ke kernel {kernel_name} ({kernel_id}) ditutup.")
            
            requests.delete(f"{JEG_BASE_URL}/api/kernels/{kernel_id}", headers=headers)
            print(f"Kernel {kernel_name} ({kernel_id}) dihapus.")
        except Exception as e:
            print(f"ERROR: Gagal cleanup kernel {kernel_name} ({kernel_id}): {e}")

    for kernel_id, result in kernel_results.items():
        print(f"Kernel ID: {kernel_id}")
        print(f"  Status: {result.get('status', 'unknown')}")
        if result.get('output'):
            print(f"  Output (awal): {result['output'].strip()[:100]}...")
        if result.get('error'):
            print(f"  Error: {result['error']}")
        if result.get('exception'):
            print(f"  Exception: {result['exception']}")
        print("-" * 30)

    print("Proses selesai.")

if __name__ == "__main__":
    main()