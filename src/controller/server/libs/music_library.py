import json
import os
import secrets
from pathlib import Path


MUSIC_DIR = Path(os.environ.get("MLSC_MUSIC_DIR", "/share/music"))
STATUS_FILE = Path(os.environ.get("MLSC_MUSIC_STATUS", "/share/.mlsc_music_status.json"))
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"}


def ensure_music_dir() -> Path:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    return MUSIC_DIR


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def safe_music_path(filename: str) -> Path:
    """Return a path inside MUSIC_DIR or raise ValueError for unsafe/unsupported names."""
    if not filename or Path(filename).name != filename:
        raise ValueError("Invalid music filename")
    if not is_supported(filename):
        raise ValueError("Unsupported audio format")

    base = ensure_music_dir().resolve()
    candidate = (base / filename).resolve()
    if candidate.parent != base:
        raise ValueError("Invalid music path")
    return candidate


def list_music_files() -> list[dict]:
    directory = ensure_music_dir()
    items = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if path.is_file() and is_supported(path.name):
            stat = path.stat()
            items.append({
                "name": path.name,
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
            })
    return items


def write_status(state: str, filename: str | None = None, error: str | None = None, *, position: float = 0, duration: float | None = None) -> None:
    payload = {"state": state, "file": filename, "error": error, "position": position, "duration": duration}
    try:
        temporary = STATUS_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload), encoding="utf-8")
        temporary.replace(STATUS_FILE)
    except OSError:
        # Status is informational only; playback must not fail because this file cannot be written.
        pass


def read_status() -> dict:
    try:
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "microphone", "file": None, "error": None}


def trash_music_file(filename: str) -> None:
    path = safe_music_path(filename)
    # Rename the named file itself; never delete a symlink's target.
    named = ensure_music_dir() / filename
    if named.is_symlink():
        raise ValueError("Cannot delete a symbolic link through the music library")
    if not path.is_file():
        raise FileNotFoundError(filename)
    trash = ensure_music_dir() / '.trash'
    if trash.is_symlink():
        raise ValueError("Invalid music trash directory")
    trash.mkdir(mode=0o700, exist_ok=True)
    bucket = trash / secrets.token_hex(8)
    bucket.mkdir(mode=0o700)
    path.rename(bucket / filename)
