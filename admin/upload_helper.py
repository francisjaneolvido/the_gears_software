# admin/upload_helper.py

import os
import subprocess
import tempfile
import requests
from dotenv import load_dotenv

load_dotenv()

# ── FFmpeg path — reads from .env, falls back to common install location ──────
FFMPEG_PATH = os.getenv("FFMPEG_PATH", r"C:\ffmpeg\bin\ffmpeg.exe")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


# ─────────────────────────────────────────────────────────────────────────────
# Thumbnail generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_video_thumbnail(video_path: str) -> str | None:
    """
    Use FFmpeg to extract a single frame (at 1 second) from a video file.

    Returns the path to a temporary .jpg thumbnail file, or None on failure.
    The caller is responsible for deleting the temp file after uploading.

    Parameters
    ----------
    video_path : str
        Absolute local path to the video file.

    Returns
    -------
    str | None
        Path to the generated thumbnail jpg, or None if FFmpeg failed.
    """
    if not os.path.exists(FFMPEG_PATH):
        print(f"[Thumbnail] ⚠ FFmpeg not found at: {FFMPEG_PATH}")
        print(f"[Thumbnail]   Set FFMPEG_PATH in your .env file.")
        return None

    if not os.path.exists(video_path):
        print(f"[Thumbnail] ⚠ Video not found: {video_path}")
        return None

    # Create a temp file for the thumbnail — same directory as video
    base     = os.path.splitext(os.path.basename(video_path))[0]
    tmp_dir  = tempfile.gettempdir()
    thumb_path = os.path.join(tmp_dir, f"{base}_thumb.jpg")

    cmd = [
        FFMPEG_PATH,
        "-y",                    # overwrite if exists
        "-i", video_path,        # input video
        "-ss", "00:00:01",       # seek to 1 second
        "-vframes", "1",         # extract exactly 1 frame
        "-vf", "scale=320:-1",   # resize to 320px wide, keep aspect ratio
        "-q:v", "3",             # JPEG quality (2=best, 5=good enough)
        thumb_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,          # don't hang forever on corrupt files
        )
        if result.returncode == 0 and os.path.exists(thumb_path):
            print(f"[Thumbnail] ✅ Generated: {thumb_path}")
            return thumb_path
        else:
            err = result.stderr.decode("utf-8", errors="ignore")[-300:]
            print(f"[Thumbnail] ❌ FFmpeg failed (code {result.returncode}): {err}")
            return None
    except subprocess.TimeoutExpired:
        print(f"[Thumbnail] ❌ FFmpeg timed out for: {video_path}")
        return None
    except Exception as exc:
        print(f"[Thumbnail] ❌ Unexpected error: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Single-file upload
# ─────────────────────────────────────────────────────────────────────────────

def _upload_single(local_path: str, flask_url: str, token: str) -> str | None:
    """
    Upload one file to Flask's /api/v1/upload endpoint.
    Returns the server-side filename on success, or None on failure.
    """
    filename = os.path.basename(local_path)
    try:
        with open(local_path, "rb") as f:
            resp = requests.post(
                f"{flask_url}/api/v1/upload",
                headers={"X-API-Token": token},
                files={"file": (filename, f)},
                timeout=60,          # videos can be large
            )
        if resp.status_code == 201:
            server_filename = resp.json()["filename"]
            print(f"[Upload] ✅ {filename} → {server_filename}")
            return server_filename
        else:
            print(f"[Upload] ❌ {filename} → HTTP {resp.status_code}: {resp.text}")
            return None
    except Exception as exc:
        print(f"[Upload] ⚠ Error uploading '{filename}': {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main public API
# ─────────────────────────────────────────────────────────────────────────────

def upload_files_to_flask(file_paths: list, flask_url: str, token: str) -> list:
    """
    Upload local files to Flask's /api/v1/upload endpoint.

    For VIDEO files:
      1. Generate a thumbnail via FFmpeg.
      2. Upload the video → get server filename.
      3. Upload the thumbnail → get server thumbnail filename.
      4. Return a media-dict: {"url": "...", "thumbnail": "...", "type": "video"}

    For IMAGE files:
      Return a media-dict: {"url": "...", "thumbnail": "...", "type": "image"}

    For already-uploaded server filenames (bare name, not on disk):
      Pass through as-is — wrapped in the same dict format if we can detect
      the type, otherwise return the raw string for backward compatibility.

    Returns
    -------
    list
        Mixed list of dicts (new format) and/or bare strings (legacy pass-through).
        admin_db_service.save_draft() already handles both via _parse_media().
    """
    uploaded = []

    for path in file_paths:
        path = str(path).strip()
        if not path:
            continue

        normalized = path.replace("\\", "/")
        filename   = normalized.split("/")[-1]
        ext        = os.path.splitext(filename)[1].lower()

        # ── Already-uploaded server filename ──────────────────────────────────
        is_bare_name = (path == filename)
        if is_bare_name and not os.path.exists(path):
            # Already on server — wrap in dict so callers get consistent format
            if ext in VIDEO_EXTENSIONS:
                uploaded.append({
                    "url":       filename,
                    "thumbnail": filename,   # no thumb available for old uploads
                    "type":      "video",
                })
            else:
                uploaded.append({
                    "url":       filename,
                    "thumbnail": filename,
                    "type":      "image",
                })
            continue

        # ── Local file ────────────────────────────────────────────────────────
        if not os.path.exists(path):
            print(f"[Upload] ⚠ File not found, skipping: {path!r}")
            uploaded.append({"url": filename, "thumbnail": filename, "type": "image"})
            continue

        if ext in VIDEO_EXTENSIONS:
            # ── Video: generate thumbnail first, then upload both ─────────────
            thumb_local = generate_video_thumbnail(path)

            server_video = _upload_single(path, flask_url, token)
            if not server_video:
                server_video = filename   # fallback to original name

            server_thumb = None
            if thumb_local:
                server_thumb = _upload_single(thumb_local, flask_url, token)
                # Clean up the temp thumbnail file
                try:
                    os.remove(thumb_local)
                except Exception:
                    pass

            uploaded.append({
                "url":       server_video,
                "thumbnail": server_thumb or server_video,  # fallback to video if no thumb
                "type":      "video",
            })

        else:
            # ── Image: upload normally ────────────────────────────────────────
            server_name = _upload_single(path, flask_url, token)
            if not server_name:
                server_name = filename

            uploaded.append({
                "url":       server_name,
                "thumbnail": server_name,
                "type":      "image",
            })

    return uploaded


# ─────────────────────────────────────────────────────────────────────────────
# Helper: get a displayable thumbnail path for the UI (local before upload)
# ─────────────────────────────────────────────────────────────────────────────

def get_local_thumbnail(local_path: str) -> str | None:
    """
    For showing a preview BEFORE uploading:
      - Images: return the path directly (PIL can open it).
      - Videos: generate a temp thumbnail and return its path.

    The returned path is a LOCAL file path suitable for PIL/ImageTk.
    The caller must NOT delete it — it lives in the temp folder and
    will be cleaned up by the OS eventually.

    Returns None if thumbnail generation fails.
    """
    ext = os.path.splitext(local_path)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return local_path
    if ext in VIDEO_EXTENSIONS:
        return generate_video_thumbnail(local_path)
    return None