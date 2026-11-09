"""
File utility functions — checksums, safe filenames, path validation.
"""

import hashlib
import os
import re
import unicodedata
from pathlib import Path


def safe_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Normalize unicode
    filename = unicodedata.normalize('NFKD', filename)
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    # Keep only safe characters
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    # Collapse multiple dots into one
    filename = re.sub(r'\.+', '.', filename)
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename or "unnamed_file"


def compute_checksum(filepath: str) -> str:
    """Compute SHA-256 checksum."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_file_size_mb(filepath: str) -> float:
    """Get file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)
    return path


def list_job_files(job_dir: str) -> list[dict]:
    """List all files in a job directory with metadata."""
    files = []
    if not os.path.exists(job_dir):
        return files

    for root, dirs, filenames in os.walk(job_dir):
        for fn in filenames:
            fpath = os.path.join(root, fn)
            rel_path = os.path.relpath(fpath, job_dir)
            files.append({
                "filename": fn,
                "relative_path": rel_path.replace('\\', '/'),
                "absolute_path": fpath,
                "size_bytes": os.path.getsize(fpath),
                "extension": os.path.splitext(fn)[1].lower(),
            })

    return sorted(files, key=lambda x: x["filename"])
