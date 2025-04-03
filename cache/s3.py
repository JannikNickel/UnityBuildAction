import os
import hashlib
import time
from log import *

from minio import Minio
from minio.error import S3Error
from concurrent.futures import ThreadPoolExecutor, as_completed

class S3Client:
    def __init__(self, server, access_key, secret_key):
        self.server = server
        self.access_key = access_key
        self.secret_key = secret_key
        self.s3 = None

    def __enter__(self):
        self.s3 = Minio(
            self.server,
            access_key = self.access_key,
            secret_key = self.secret_key,
            secure = True
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass # Minio closes connections automatically

    @staticmethod
    def normalize_path(*parts):
        return os.path.join(*parts).replace("\\", "/")
    
    @staticmethod
    def compute_file_hash(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        return (hashlib.sha256(data).hexdigest(), len(data))

    @staticmethod
    def retry(operation, retries = 3, delay = 0.1):
        for i in range(retries):
            try:
                return operation()
            except Exception as e:
                if i == retries - 1:
                    log("S3", f"Operation failed after {retries} retries: {e}")
                    return False
                time.sleep(delay * (i + 1))
    
    def can_skip_file(self, bucket, object_name, local_path, hash, size):
        try:
            stat = self.s3.stat_object(bucket, object_name)
            return stat.size == size and stat.metadata and stat.metadata.get("x-amz-meta-sha256") == hash
        except:
            return False
        
    def upload_file(self, bucket, object_name, file):
        hash, size = self.compute_file_hash(file)

        if self.can_skip_file(bucket, object_name, file, hash, size):
            return False
        
        def operation():
            self.s3.fput_object(bucket, object_name, file, metadata = { "sha256": hash })
            return True
        return self.retry(operation)
    
    def download_file(self, bucket, object_name, file):        
        def operation():
            self.s3.fget_object(bucket, object_name, file)
            return True
        return self.retry(operation)
    
    def upload_directory(self, local_dir, bucket, remote_prefix, workers = 8, progress_callback = None, callback_interval = 1.0):
        if not self.s3.bucket_exists(bucket):
            log("S3", f"Bucket {bucket} does not exist. Skipping upload")
            return

        all_files = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                full_path = self.normalize_path(root, file)
                relative_path = os.path.relpath(full_path, local_dir)
                s3_key = f"{remote_prefix}{relative_path}"
                all_files.append((full_path, s3_key))

        log("S3", f"Starting upload of {len(all_files)} files with {workers} threads...")

        uploaded = 0
        skipped = 0
        total_files = len(all_files)
        last_callback_time = time.time()

        with ThreadPoolExecutor(workers) as executor:
            futures = {
                executor.submit(self.upload_file, bucket, s3_key, full_path): idx
                for idx, (full_path, s3_key) in enumerate(all_files, 1)
            }

            for future in as_completed(futures):
                result = future.result()
                uploaded += result
                skipped += not result

                now = time.time()
                if progress_callback and (now - last_callback_time) >= callback_interval:
                    progress = (uploaded + skipped) / float(total_files) * 100.0
                    progress_callback(progress)
                    last_callback_time = now

        if progress_callback:
            progress_callback(100.0)
        log("S3", f"Upload completed! {uploaded} uploaded, {skipped} skipped")

        return [s3_key for _, s3_key in all_files]

    def delete_keys(self, bucket, prefix, exceptions, progress_callback = None, callback_interval = 1.0):
        if not self.s3.bucket_exists(bucket):
            log("S3", f"Bucket {bucket} does not exist. Skipping delete")
            return
        
        exceptions_set = set(exceptions)
        log("S3", f"Finding unused files in {bucket}/{prefix}...")
        objects = self.s3.list_objects(bucket, prefix, True)
        objects = [obj for obj in objects if obj.object_name not in exceptions_set]

        deleted = 0
        total_objects = len(objects)
        last_callback_time = time.time()

        deleted = 0
        for obj in objects:
            try:
                self.s3.remove_object(bucket, obj.object_name)
                deleted += 1
            except S3Error as e:
                log("S3", f"Failed to delete {obj.object_name}")

            now = time.time()
            if progress_callback and (now - last_callback_time) >= callback_interval:
                progress = deleted / float(total_objects) * 100.0
                progress_callback(progress)
                last_callback_time = now 
        
        log("S3", f"Deleted {deleted} out of {len(objects)} unused files from {bucket}/{prefix}")

    def download_directory(self, local_dir, bucket, remote_prefix, workers = 8, progress_callback = None, callback_interval = 1.0):
        if not self.s3.bucket_exists(bucket):
            log("S3", f"Bucket {bucket} does not exist. Skipping download")
            return

        all_files = []
        log("S3", f"Listing files in {bucket}/{remote_prefix}...")
        objects = self.s3.list_objects(bucket, remote_prefix, True)
        for obj in objects:
            relative_path = os.path.relpath(obj.object_name, remote_prefix)
            local_path = self.normalize_path(local_dir, relative_path)
            all_files.append((local_path, obj.object_name))

        log("S3", f"Starting download of {len(all_files)} files with {workers} threads...")

        downloaded = 0
        total_files = len(all_files)
        last_callback_time = time.time()

        with ThreadPoolExecutor(workers) as executor:
            futures = {
                executor.submit(self.download_file, bucket, object_name, local_path): idx
                for idx, (local_path, object_name) in enumerate(all_files, 1)
            }

            for future in as_completed(futures):
                future.result()
                downloaded += 1

                now = time.time()
                if progress_callback and (now - last_callback_time) >= callback_interval:
                    progress = downloaded / float(total_files) * 100.0
                    progress_callback(progress)
                    last_callback_time = now

        if progress_callback:
            progress_callback(100.0)
        log("S3", f"Download completed! {downloaded} files downloaded")
