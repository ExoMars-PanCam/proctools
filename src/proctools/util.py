import hashlib
from pathlib import Path


def get_md5sum(path: Path):
    """Generate the md5 hash for a file in chunks, providing a low memory footprint"""
    md5 = hashlib.md5()
    with open(path, "rb", buffering=0) as f:
        while True:
            data = f.read(131072)  # buffer = 128*1024 bytes
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()
