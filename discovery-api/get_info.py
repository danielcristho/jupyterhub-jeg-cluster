import requests
import json
import time
from datetime import timedelta

dashboard_url = "http://10.21.73.122:18265"

nodes_endpoint = "/nodes?view=summary"

try:
    # Mengambil data dari API
    response = requests.get(f"{dashboard_url}{nodes_endpoint}")
    response.raise_for_status()
    nodes_data = response.json()

    summary_data = nodes_data["data"]["summary"]

    print("Ray Cluster Nodes Uptime:")
    print("-" * 50)

    for node_info in summary_data:
        node_id = node_info.get("nodeId", "Unknown")
        ip_address = node_info.get("ip", "Unknown")
        hostname = node_info.get("hostname", "Unknown")

        # Get startTimeMs from raylet
        raylet_info = node_info.get("raylet", {})
        start_time_ms = int(raylet_info.get("startTimeMs", 0))
        current_time = node_info.get("now", time.time())

        uptime_seconds = current_time - (start_time_ms / 1000)
        uptime_delta = timedelta(seconds=uptime_seconds)

        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        is_head = "Yes" if raylet_info.get("isHeadNode", False) else "No"

        print(f"Node: {hostname} ({ip_address})")
        print(f"Node ID: {node_id}")
        print(f"Head Node: {is_head}")
        print(f"Uptime: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds")
        print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_ms/1000))}")
        print("-" * 50)

except requests.exceptions.RequestException as e:
    print(f"Error fetching data from Ray Dashboard: {e}")
except (KeyError, ValueError, TypeError) as e:
    print(f"Error parsing response data: {e}")
