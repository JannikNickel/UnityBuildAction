from dotenv import load_dotenv
import os

PROXMOX_HOST = None
NODE = None
RUNNER_VMID = None
BACKUP_STORAGE = None
RUNNER_BACKUP = None
API_USER = None
API_TOKEN = None

def initialize(dotenv_path = None):
    load_dotenv(dotenv_path)

    global PROXMOX_HOST, NODE, RUNNER_VMID, BACKUP_STORAGE, RUNNER_BACKUP, API_USER, API_TOKEN
    PROXMOX_HOST = os.getenv("PVE_PROXMOX_HOST")
    NODE = os.getenv("PVE_NODE")
    RUNNER_VMID = os.getenv("PVE_RUNNER_VMID")
    BACKUP_STORAGE = os.getenv("PVE_BACKUP_STORAGE")
    RUNNER_BACKUP = os.getenv("PVE_RUNNER_BACKUP")
    API_USER = os.getenv("PVE_API_USER")
    API_TOKEN = os.getenv("PVE_API_TOKEN")
