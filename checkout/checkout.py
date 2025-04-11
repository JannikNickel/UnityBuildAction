import os
import subprocess
import shutil
from log import *

REPOSITORY = os.getenv("INPUT_REPOSITORY")
REF = os.getenv("INPUT_REF")
TOKEN = os.getenv("INPUT_TOKEN")
PATH = os.getenv("INPUT_PATH", "")

assert(REPOSITORY)
assert(REF)
assert(TOKEN)
PATH = os.path.abspath(os.path.join(os.getcwd(), PATH))

def run_subprocess(command):
    result = subprocess.run(
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True
    )
    return result

def run_subprocess_async(command):
    process = subprocess.Popen(
        command,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        text = True
    )
    for line in process.stdout:
        print(line, end = "")
    process.wait()
    return process.returncode

def repo_exists():
    if not os.path.isdir(os.path.join(PATH, ".git")):
        return False
    
    result = run_subprocess(["git", "-C", PATH, "config", "--get", "remote.origin.url"])
    remote_url = result.stdout.strip()
    return REPOSITORY in remote_url

def main():
    log("CHECKOUT", f"Starting checkout process... Path: {PATH}")
    exists = repo_exists()

    if not exists:
        if os.path.exists(PATH):
            log("CHECKOUT", "Repository does not match, clearing destination path")
            for root, dirs, files in os.walk(PATH):
                for d in dirs:
                    os.chmod(os.path.join(root, d), 0o777)
                for f in files:
                    os.chmod(os.path.join(root, f), 0o777)
            shutil.rmtree(PATH)
        
    if not exists:
        log("CHECKOUT", "Cloning repository")
        result = run_subprocess_async(
            ["git", "clone", f"https://{TOKEN}@github.com/{REPOSITORY}.git", PATH]
        )
        if result != 0:
            raise RuntimeError(f"Failed to clone repository: {result}")

    log("CHECKOUT", "Clearing open changes")
    result = run_subprocess_async(["git", "-C", PATH, "reset", "--hard"])
    if result != 0:
        raise RuntimeError(f"Failed to reset repository: {result}")
    
    log("CHECKOUT", "Fetch the reference")
    result = run_subprocess_async(["git", "-C", PATH, "fetch", "origin", REF])
    if result != 0:
        raise RuntimeError(f"Failed to fetch reference {REF}: {result}")

    log("CHECKOUT", "Checking out reference")
    result = run_subprocess_async(["git", "-C", PATH, "checkout", "FETCH_HEAD"])
    if result != 0:
        raise RuntimeError(f"Failed to checkout reference {REF}: {result}")

main()
