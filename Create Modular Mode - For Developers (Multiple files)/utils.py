import hashlib
from pathlib import Path
from datetime import datetime

VERSION = "2.1.0"

SUPPORTED_EXT = {
    ".jpg", ".jpeg", ".tiff", ".tif",
    ".png", ".webp", ".heic", ".heif",
    ".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng",
    ".bmp", ".gif",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mts", ".m2ts"
}

EXIFREAD_EXT = {".jpg", ".jpeg", ".tiff", ".tif"}
PILLOW_EXT   = {".png", ".webp", ".bmp", ".gif", ".heic", ".heif"}
RAW_EXT      = {".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng"}
VIDEO_EXT    = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".mts", ".m2ts"}

ASCII_BANNER = """
  /\\_____/\\
 /  o   o  \\
( ==  ^  == )
 )  C A T  (
(  I F Y   )
 \\ ExFin  /
  '-------'
"""

DEFAULT_SANITIZE_MAX_LENGTH = 200


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def get_size_str(path: Path) -> str:
    try:
        size = path.stat().st_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except Exception:
        return "N/A"


def get_mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def sanitize_value(value, max_length: int = DEFAULT_SANITIZE_MAX_LENGTH) -> str:
    text = str(value)
    sanitized_chars = []
    visible_length = 0
    truncated = False

    for char in text:
        if char.isprintable():
            part = char
        else:
            part = f"\\x{ord(char):02x}"

        if visible_length + len(part) > max_length:
            truncated = True
            break

        sanitized_chars.append(part)
        visible_length += len(part)

    result = "".join(sanitized_chars)
    if truncated:
        result += "..."
    return result


def sanitize_exif_dict(exif: dict, max_length: int = DEFAULT_SANITIZE_MAX_LENGTH) -> dict:
    return {
        sanitize_value(tag, max_length): sanitize_value(val, max_length)
        for tag, val in exif.items()
    }
