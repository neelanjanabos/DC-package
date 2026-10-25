"""
Video Compression - Video Metadata Extraction Module
Uses FFprobe to extract detailed technical metadata from video files.
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Dict, Any, Optional


def find_executable(name: str) -> Optional[str]:
    """
    Locates an executable by name across PATH, local app data, and WinGet links.
    Ensures compatibility across fresh installations on Windows and Unix.
    """
    # 1. Standard PATH check
    path = shutil.which(name)
    if path and os.path.isfile(path):
        return path

    # 2. Windows specific common install locations
    if sys.platform == "win32":
        # Check WinGet Links directory
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            winget_link = os.path.join(local_app_data, "Microsoft", "WinGet", "Links", f"{name}.exe")
            if os.path.isfile(winget_link):
                return winget_link

            # Check WinGet Packages directory
            packages_dir = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
            if os.path.isdir(packages_dir):
                for root, _, files in os.walk(packages_dir):
                    if f"{name}.exe" in files:
                        candidate = os.path.join(root, f"{name}.exe")
                        if os.path.isfile(candidate):
                            return candidate

        # Check standard Program Files
        for pf in ["ProgramFiles", "ProgramFiles(x86)"]:
            pf_dir = os.environ.get(pf, "")
            if pf_dir:
                candidate = os.path.join(pf_dir, "ffmpeg", "bin", f"{name}.exe")
                if os.path.isfile(candidate):
                    return candidate

        # Refresh PATH from registry if possible
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                sys_path = winreg.QueryValueEx(key, "Path")[0]
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                usr_path = winreg.QueryValueEx(key, "Path")[0]
            combined_path = sys_path + ";" + usr_path
            path = shutil.which(name, path=combined_path)
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass

    return None


def get_ffprobe_path() -> str:
    """Returns the absolute path to ffprobe or raises FileNotFoundError."""
    path = find_executable("ffprobe")
    if not path:
        raise FileNotFoundError(
            "ffprobe executable not found in PATH or standard directories. "
            "Please ensure FFmpeg (which includes ffprobe) is installed."
        )
    return path


def format_bytes(size_bytes: int) -> str:
    """Formats bytes into human-readable string (KB, MB, GB)."""
    if size_bytes < 0:
        return f"-{format_bytes(abs(size_bytes))}"
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def extract_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extracts comprehensive video and audio metadata from a media file using ffprobe.
    
    Returns a dictionary containing:
      - filename: str
      - file_size_bytes: int
      - file_size_formatted: str
      - duration_seconds: float
      - duration_formatted: str
      - width: int
      - height: int
      - resolution: str
      - frame_rate: float
      - video_codec: str
      - audio_codec: Optional[str]
      - has_audio: bool
      - bitrate_kbps: float
      - format_name: str
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Video file does not exist: {file_path}")

    ffprobe_cmd = get_ffprobe_path()

    cmd = [
        ffprobe_cmd,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=30
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFprobe failed to inspect file: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise TimeoutError("FFprobe command timed out while inspecting video.")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse FFprobe JSON output: {e}")

    format_info = data.get("format", {})
    streams = data.get("streams", [])

    video_stream = None
    audio_stream = None

    for s in streams:
        c_type = s.get("codec_type")
        if c_type == "video" and video_stream is None:
            video_stream = s
        elif c_type == "audio" and audio_stream is None:
            audio_stream = s

    file_size_bytes = os.path.getsize(file_path)

    # Duration parsing (fallback from format to video stream)
    raw_duration = format_info.get("duration")
    if not raw_duration and video_stream:
        raw_duration = video_stream.get("duration")
    try:
        duration_seconds = float(raw_duration) if raw_duration else 0.0
    except (ValueError, TypeError):
        duration_seconds = 0.0

    # Video stream properties
    width = 0
    height = 0
    frame_rate = 0.0
    video_codec = "Unknown"

    if video_stream:
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        video_codec = video_stream.get("codec_name", "Unknown").upper()

        fps_str = video_stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = fps_str.split("/", 1)
            try:
                num_f, den_f = float(num), float(den)
                frame_rate = (num_f / den_f) if den_f != 0 else 0.0
            except (ValueError, ZeroDivisionError):
                frame_rate = 0.0
        else:
            try:
                frame_rate = float(fps_str)
            except ValueError:
                frame_rate = 0.0

    # Audio stream properties
    has_audio = audio_stream is not None
    audio_codec = audio_stream.get("codec_name", "").upper() if audio_stream else None

    # Bitrate calculation
    raw_bitrate = format_info.get("bit_rate")
    if not raw_bitrate and video_stream:
        raw_bitrate = video_stream.get("bit_rate")
    try:
        bitrate_kbps = (float(raw_bitrate) / 1000.0) if raw_bitrate else 0.0
    except (ValueError, TypeError):
        bitrate_kbps = 0.0

    if bitrate_kbps == 0.0 and duration_seconds > 0:
        bitrate_kbps = ((file_size_bytes * 8) / duration_seconds) / 1000.0

    resolution = f"{width}x{height}" if width and height else "Unknown"

    return {
        "filename": os.path.basename(file_path),
        "file_path": file_path,
        "file_size_bytes": file_size_bytes,
        "file_size_formatted": format_bytes(file_size_bytes),
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
        "duration_seconds": round(duration_seconds, 2),
        "duration_formatted": format_duration(duration_seconds),
        "width": width,
        "height": height,
        "resolution": resolution,
        "frame_rate": round(frame_rate, 2),
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "has_audio": has_audio,
        "bitrate_kbps": round(bitrate_kbps, 2),
        "format_name": format_info.get("format_name", "Unknown"),
    }
