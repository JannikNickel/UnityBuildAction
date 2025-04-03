import os

from log import *
from s3 import S3Client

SERVER = os.getenv("INPUT_SERVER")
SERVER_ACCESS_KEY = os.getenv("INPUT_SERVER_ACCESS_KEY")
SERVER_SECRET_KEY = os.getenv("INPUT_SERVER_SECRET_KEY")
SERVER_BUCKET = os.getenv("INPUT_SERVER_BUCKET")
ID = os.getenv("INPUT_ID")
PATH = os.getenv("INPUT_PATH")
CLEAR_EXISTING = os.getenv("INPUT_CLEAR_EXISTING", "false").lower() == "true"
ACTION = os.getenv("INPUT_ACTION", "cache").lower()

PATH = os.path.abspath(os.path.join(os.getcwd(), PATH))

assert(SERVER)
assert(SERVER_ACCESS_KEY)
assert(SERVER_SECRET_KEY)
assert(SERVER_BUCKET)
assert(ID)
assert(PATH)

def cache():
    if not os.path.exists(PATH):
        log("CACHE", f"The specified path directory does not exist: {PATH}... Skipping cache")
        return

    with S3Client(SERVER, SERVER_ACCESS_KEY, SERVER_SECRET_KEY) as s3:
        remote_prefix = s3.normalize_path(ID)
        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        log("CACHE", f"Cache local directory {PATH} to remote path {SERVER_BUCKET}/{remote_prefix}")
        keys = s3.upload_directory(PATH, SERVER_BUCKET, remote_prefix, 8, lambda p: log("CACHE", f"Uploading to cache {p:.1f}%"))

        if CLEAR_EXISTING:
            log("CACHE", f"Clear unused files in remote path {SERVER_BUCKET}/{remote_prefix}")
            s3.delete_keys(SERVER_BUCKET, remote_prefix, keys, lambda p: log("CACHE", f"Deleting unused files {p:.1f}%"))

def restore():
    if not os.path.exists(PATH):
        os.makedirs(PATH)

    with S3Client(SERVER, SERVER_ACCESS_KEY, SERVER_SECRET_KEY) as s3:
        remote_prefix = s3.normalize_path(ID)
        if not remote_prefix.endswith("/"):
            remote_prefix += "/"

        log("CACHE", f"Restore remote cache {SERVER_BUCKET}/{remote_prefix} to local directory {PATH}")
        s3.download_directory(PATH, SERVER_BUCKET, remote_prefix, 8, lambda p: log("CACHE", f"Restoring from cache {p:.1f}%"))

if ACTION == "cache":
    cache()
elif ACTION == "restore":
    restore()
else:
    log("CACHE", f"Unknown action: {ACTION}")
