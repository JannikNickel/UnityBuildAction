import os
import config

BOOTSTRAPPER_PATH = os.path.abspath(os.path.join(os.getcwd(), os.getenv("INPUT_BOOTSTRAPPER_PATH")))
config.initialize(BOOTSTRAPPER_PATH)

import proxmox_vm

# Wait for the VM to be stopped, otherwise it is currently running a workflow
proxmox_vm.wait_vm_status(config.RUNNER_VMID, "stopped")

# Restore the VM from the latest backup to ensure a clean state
backup_volid = config.RUNNER_BACKUP or proxmox_vm.get_latest_backup_filename(config.RUNNER_VMID, config.BACKUP_STORAGE)
proxmox_vm.restore_vm_backup(config.RUNNER_VMID, backup_volid)

# Start the VM
proxmox_vm.start_vm(config.RUNNER_VMID)
proxmox_vm.wait_vm_status(config.RUNNER_VMID, "running")
