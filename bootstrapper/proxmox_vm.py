# API Docs: https://pve.proxmox.com/pve-docs/api-viewer
# For more info: Use dev tools in browser to see the requests made by the web interface

import requests
import time
from config import PROXMOX_HOST, NODE, API_USER, API_TOKEN

HEADERS = {
    "Authorization": f"PVEAPIToken={API_USER}={API_TOKEN}"
}

def get(url):
    resp = requests.get(url, headers = HEADERS)
    resp.raise_for_status()
    return resp.json()

def post(url, data = None):
    resp = requests.post(url, data = data, headers = HEADERS)
    resp.raise_for_status()
    return resp.json()

def get_vm_status(vmid):
    json = get(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{vmid}/status/current")
    return json["data"]["status"]

def start_vm(vmid):
    post(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{vmid}/status/start")
    print(f"VM {vmid} start requested")

def stop_vm(vmid):
    post(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{vmid}/status/stop")
    print(f"VM {vmid} stop requested")

def wait_vm_status(vmid, desired_status, interval = 5):
    print(f"Waiting for VM {vmid} to be in \"{desired_status}\" state...")
    while True:
        status = get_vm_status(vmid)
        print(f"  Current status: {status}")
        if status == desired_status:
            break
        time.sleep(interval)

def get_latest_backup_filename(vmid, backup_storage):
    json = get(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/storage/{backup_storage}/content")
    backups = [content for content in json["data"] if content["content"] == "backup" and f"vzdump-qemu-{vmid}-" in content["volid"]]
    backups.sort(key = lambda n: n["ctime"], reverse = True)
    return backups[0]["volid"] if backups else None

def wait_for_task_completion(upid, interval = 5, timeout = 900):
    start_time = time.time()
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/tasks/{upid}/status"
    
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            raise TimeoutError("Timeout")
        
        status_resp = get(url)
        status = status_resp["data"]["status"]
        if status == "stopped":
            exitstatus = status_resp["data"]["exitstatus"]
            if exitstatus == "OK":
                print("Restore completed successfully.")
                return
            else:
                raise Exception(f"Restore failed: {exitstatus}")
        print(f"  Current status: {status}")
        time.sleep(interval)

def restore_vm_backup_by_filename(vmid, backup_storage, file):
    restore_vm_backup(vmid, f"{backup_storage}:backup/{file}")

def restore_vm_backup(vmid, volid):
    print(f"Restoring backup {volid} to VM {vmid}...")
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu"
    resp = post(url, data = {
        "vmid": vmid,
        "archive": volid,
        "force": 1,
        "unique": 0
    })

    print("Restore started. Waiting for a completion...")
    wait_for_task_completion(resp["data"])
