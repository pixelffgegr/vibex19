"""Regression check for the read-only-filesystem download cache.

GetFileFromS3 used to mirror every S3 download into ./download_cache
unconditionally. Serverless lambdas have a read-only filesystem, so any image
that was not already in the bucket - a freshly rendered thumbnail, a new crop
size - raised OSError [Errno 30] and the request became an HTTP 500.

Run from the project root:
    syntaxsource/syntaxwebsite/venv/Scripts/python tools/verify_readonly_cache.py
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE = os.path.join(ROOT, "syntaxsource", "syntaxwebsite")
sys.path.insert(0, WEBSITE)
os.environ["DISABLE_SCHEDULER"] = "1"
os.chdir(WEBSITE)

from app import create_app  # noqa: E402,F401
from app.util import s3helper  # noqa: E402
from config import Config  # noqa: E402

failures = []


def check(ok, label, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + label + (f"   {detail}" if detail else ""))
    if not ok:
        failures.append(label)


print(f"USE_LOCAL_STORAGE={Config.USE_LOCAL_STORAGE}  cache dir={Config.AWS_S3_DOWNLOAD_CACHE_DIR}")

# Pick a real object that is already in storage.
with tempfile.NamedTemporaryFile("wb", suffix=".blocker", delete=False) as blocker:
    blocker.write(b"i am a file, not a directory")
    blocker_path = blocker.name

readonly_dir = os.path.join(blocker_path, "download_cache")
original_dir = s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR
original_local = s3helper.Config.USE_LOCAL_STORAGE
try:
    s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR = readonly_dir

    # Prove the directory really is unwritable the way a lambda's is.
    try:
        os.makedirs(readonly_dir, exist_ok=True)
        check(False, "test setup: cache dir is unwritable")
    except OSError as exc:
        check(True, "test setup: cache dir is unwritable", f"{type(exc).__name__}")

    probe = None
    contents = s3helper.getS3Client().list_objects_v2(Bucket=s3helper.Config.AWS_S3_BUCKET_NAME).get("Contents")
    if contents:
        probe = contents[0]["Key"]
    check(probe is not None, "found an object in the bucket to download")

    if probe is not None:
        data = s3helper.GetFileFromS3(probe)
        check(isinstance(data, bytes) and len(data) > 0, "GetFileFromS3 returns bytes with an unwritable cache", f"{type(data).__name__} len={len(data) if data else 0}")

    # And the local-development path must still use the disk as its store.
    s3helper.Config.USE_LOCAL_STORAGE = True
    original_local_dir = original_dir
    s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR = os.path.join(tempfile.gettempdir(), "vibex19_local_cache_check")
    os.makedirs(s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR, exist_ok=True)
    url = s3helper.UploadBytesToS3(b"local-mode-check", "local_mode_probe")
    on_disk = os.path.exists(os.path.join(s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR, "local_mode_probe"))
    check(on_disk, "USE_LOCAL_STORAGE=True still writes to the cache dir", url)
    back = s3helper.GetFileFromS3("local_mode_probe")
    check(back == b"local-mode-check", "USE_LOCAL_STORAGE=True round-trips through the cache dir", repr(back))
finally:
    s3helper.Config.AWS_S3_DOWNLOAD_CACHE_DIR = original_dir
    s3helper.Config.USE_LOCAL_STORAGE = original_local
    try:
        os.remove(blocker_path)
    except OSError:
        pass

print()
if failures:
    print("RESULT: FAIL -> " + "; ".join(failures))
    sys.exit(1)
print("RESULT: all passed")