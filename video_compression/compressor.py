"""
Video Compression - Compression Engine
Implements H.264/MPEG-4 Part 10 AVC video compression using FFmpeg and libx264.
"""

import os
import sys
import time
import shutil
import subprocess
from typing import Dict, Any, Optional, Tuple, Callable

from video_metadata import find_executable, format_bytes, extract_metadata


def get_ffmpeg_path() -> str:
    """Returns the absolute path to ffmpeg or raises FileNotFoundError."""
    path = find_executable("ffmpeg")
    if not path:
        raise FileNotFoundError(
            "ffmpeg executable not found in PATH or standard directories. "
            "Please ensure FFmpeg is installed and accessible."
        )
    return path


def check_ffmpeg_support() -> Dict[str, Any]:
    """
    Checks if ffmpeg is available and whether libx264 encoder is compiled in.
    Returns status dictionary with version and capability flags.
    """
    ffmpeg_path = find_executable("ffmpeg")
    if not ffmpeg_path:
        return {
            "available": False,
            "path": None,
            "version": None,
            "has_libx264": False,
            "error": "FFmpeg executable not found on the system."
        }

    try:
        ver_result = subprocess.run(
            [ffmpeg_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        version_line = ver_result.stdout.splitlines()[0] if ver_result.stdout else "Unknown"

        encoders_result = subprocess.run(
            [ffmpeg_path, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=True
        )
        has_libx264 = "libx264" in encoders_result.stdout

        return {
            "available": True,
            "path": ffmpeg_path,
            "version": version_line,
            "has_libx264": has_libx264,
            "error": None if has_libx264 else "libx264 encoder not enabled in FFmpeg."
        }
    except Exception as e:
        return {
            "available": False,
            "path": ffmpeg_path,
            "version": None,
            "has_libx264": False,
            "error": str(e)
        }


def build_scale_filter(target_resolution: str, orig_width: int, orig_height: int) -> Optional[str]:
    """
    Constructs an FFmpeg scale filter based on chosen resolution preset.
    Ensures width and height are divisible by 2 for H.264 macroblock constraints.
    """
    if not target_resolution or target_resolution.startswith("Original"):
        return None

    resolution_map = {
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
        "360p": 360
    }

    target_h = None
    for key, h in resolution_map.items():
        if key.lower() in target_resolution.lower():
            target_h = h
            break

    if target_h is None:
        return None

    # Only downscale; don't upscale lower-resolution source
    if orig_height > 0 and orig_height <= target_h:
        return None

    # scale=-2:height guarantees width is kept proportional and even
    return f"scale=-2:{target_h}"


def compress_video(
    input_path: str,
    output_path: str,
    crf: int = 28,
    preset: str = "medium",
    target_resolution: str = "Original",
    preserve_audio: bool = True,
    audio_bitrate: str = "128k"
) -> Dict[str, Any]:
    """
    Compresses a video file using FFmpeg and libx264 (H.264/MPEG-4 Part 10 AVC).

    Parameters:
      - input_path: Path to the input video.
      - output_path: Destination path for compressed MP4 file.
      - crf: Constant Rate Factor (18 to 51, default 28).
             Lower = higher quality and larger file size.
             Higher = lower quality and smaller file size.
      - preset: H.264 encoding speed/efficiency preset (ultrafast to veryslow).
      - target_resolution: 'Original', '1080p', '720p', '480p', '360p'.
      - preserve_audio: True to re-encode audio to AAC, False to strip audio.
      - audio_bitrate: Target audio bitrate if preserved (e.g. '128k').

    Returns:
      Dictionary with compression results, metrics, and encoding time.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    support = check_ffmpeg_support()
    if not support["available"]:
        raise RuntimeError(f"FFmpeg is not available: {support['error']}")
    if not support["has_libx264"]:
        raise RuntimeError("FFmpeg is available, but the 'libx264' encoder is missing.")

    ffmpeg_path = support["path"]

    # Extract source metadata to verify streams
    meta_orig = extract_metadata(input_path)
    orig_size = meta_orig["file_size_bytes"]
    has_audio = meta_orig["has_audio"]
    orig_w = meta_orig["width"]
    orig_h = meta_orig["height"]

    # Clamp CRF within valid range
    crf = max(0, min(51, int(crf)))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Build FFmpeg command arguments
    cmd = [ffmpeg_path, "-y", "-i", input_path]

    # Video filters (scaling)
    scale_filter = build_scale_filter(target_resolution, orig_w, orig_h)
    if scale_filter:
        cmd.extend(["-vf", scale_filter])

    # H.264 Video Encoding Options
    cmd.extend([
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p"  # Maximum cross-platform and browser compatibility
    ])

    # Audio Options
    if preserve_audio and has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate])
    else:
        cmd.append("-an")

    # Faststart: puts the moov atom at beginning of MP4 for immediate browser playback
    cmd.extend(["-movflags", "+faststart", output_path])

    # Measure exact encoding time
    start_time = time.perf_counter()

    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=600,
            check=True
        )
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.strip() if e.stderr else "Unknown FFmpeg error"
        # Clean up partial output if created
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        raise RuntimeError(f"FFmpeg compression failed: {stderr_output}")
    except subprocess.TimeoutExpired:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        raise TimeoutError("Compression timed out after 600 seconds.")

    end_time = time.perf_counter()
    encoding_time_seconds = round(end_time - start_time, 2)

    if not os.path.isfile(output_path):
        raise FileNotFoundError(f"Expected compressed output was not produced: {output_path}")

    compressed_size = os.path.getsize(output_path)

    # Calculate Data Compression Metrics
    storage_saved = orig_size - compressed_size
    storage_reduction_pct = ((orig_size - compressed_size) / orig_size * 100.0) if orig_size > 0 else 0.0
    compression_ratio = (orig_size / compressed_size) if compressed_size > 0 else 0.0

    # Extract compressed video metadata
    meta_comp = extract_metadata(output_path)

    return {
        "success": True,
        "input_path": input_path,
        "output_path": output_path,
        "crf": crf,
        "preset": preset,
        "original_size_bytes": orig_size,
        "original_size_formatted": format_bytes(orig_size),
        "compressed_size_bytes": compressed_size,
        "compressed_size_formatted": format_bytes(compressed_size),
        "storage_saved_bytes": storage_saved,
        "storage_saved_formatted": format_bytes(storage_saved),
        "storage_reduction_pct": round(storage_reduction_pct, 2),
        "compression_ratio": round(compression_ratio, 2),
        "encoding_time_seconds": encoding_time_seconds,
        "is_size_increased": compressed_size > orig_size,
        "command_executed": " ".join(cmd),
        "original_metadata": meta_orig,
        "compressed_metadata": meta_comp
    }
