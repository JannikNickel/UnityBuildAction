import os
import config
from log import *
from filelock import LockFile

LOCK_TIMEOUT = 3600

BOOTSTRAPPER_PATH_VAR = os.getenv("INPUT_BOOTSTRAPPER_PATH")
BOOTSTRAPPER_PATH = os.path.abspath(os.path.join(os.getcwd(), BOOTSTRAPPER_PATH_VAR))
ENV_FILE_PATH = os.path.join(BOOTSTRAPPER_PATH, ".env")
LOCK_FILE_PATH = os.path.join(BOOTSTRAPPER_PATH, ".lock")
log("BOOTSTRAPPER", f"Loading config: {ENV_FILE_PATH}")
config.initialize(ENV_FILE_PATH)

import proxmox_vm

try:
    log("BOOTSTRAPPER", "Acquiring lock...")
    with LockFile(LOCK_FILE_PATH, timeout = LOCK_TIMEOUT):
        # Wait for the VM to be stopped, otherwise it is currently running a workflow
        proxmox_vm.wait_vm_status(config.RUNNER_VMID, "stopped")

        # Restore the VM from the latest backup to ensure a clean state
        backup_volid = config.RUNNER_BACKUP or proxmox_vm.get_latest_backup_filename(config.RUNNER_VMID, config.BACKUP_STORAGE)
        proxmox_vm.restore_vm_backup(config.RUNNER_VMID, backup_volid)

        # Start the VM
        proxmox_vm.start_vm(config.RUNNER_VMID)
        proxmox_vm.wait_vm_status(config.RUNNER_VMID, "running")
except TimeoutError as e:
    log("BOOTSTRAPPER", str(e))
    raise e
