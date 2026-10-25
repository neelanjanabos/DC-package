"""
Video Compression - Automated Test Suite
Generates a test video using FFmpeg, validates metadata extraction, performs actual
compression, tests formulas and calculations, and validates output playability.
"""

import os
import sys
import subprocess

# Ensure local modules can be imported
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from video_metadata import extract_metadata, format_bytes, get_ffprobe_path
from compressor import compress_video, check_ffmpeg_support, get_ffmpeg_path


def generate_synthetic_test_video(output_path: str, duration_sec: int = 4) -> str:
    """
    Generates a synthetic high-bitrate test video with testsrc and sine audio.
    """
    ffmpeg_exe = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration_sec}:size=1280x720:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_sec}",
        "-c:v", "libx264", "-crf", "14", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_path


def run_tests():
    print("=" * 60)
    print("RUNNING AUTOMATED TESTS FOR: Video Compression")
    print("=" * 60)

    # 1. Environment and Support Verification
    print("\n[Test 1] Checking FFmpeg and libx264 capability...")
    support = check_ffmpeg_support()
    assert support["available"] is True, f"FFmpeg not available: {support['error']}"
    assert support["has_libx264"] is True, "libx264 encoder is missing in FFmpeg build"
    ffprobe_path = get_ffprobe_path()
    assert os.path.isfile(ffprobe_path), f"FFprobe executable not found at {ffprobe_path}"
    print(f"  --> PASS: FFmpeg ready ({support['path']})")
    print(f"  --> PASS: FFprobe ready ({ffprobe_path})")

    # 2. Synthetic Test Video Generation
    test_input = os.path.join(PROJECT_DIR, "uploads", "test_sample_720p.mp4")
    print(f"\n[Test 2] Generating synthetic 720p test video at: {test_input}...")
    generate_synthetic_test_video(test_input, duration_sec=4)
    assert os.path.isfile(test_input), "Failed to generate test sample video"
    print(f"  --> PASS: Sample video created ({format_bytes(os.path.getsize(test_input))})")

    # 3. Metadata Extraction Verification
    print("\n[Test 3] Extracting original video metadata...")
    meta = extract_metadata(test_input)
    assert meta["width"] == 1280, f"Expected width 1280, got {meta['width']}"
    assert meta["height"] == 720, f"Expected height 720, got {meta['height']}"
    assert meta["has_audio"] is True, "Expected audio stream"
    assert meta["file_size_bytes"] > 0, "File size must be positive"
    assert meta["duration_seconds"] >= 3.9, f"Duration mismatch: {meta['duration_seconds']}"
    print(f"  --> PASS: Metadata verified: {meta['resolution']}, {meta['duration_formatted']}, {meta['video_codec']}/{meta['audio_codec']}")

    # 4. Actual Compression Execution (CRF 28, Scale to 480p)
    test_output_crf28 = os.path.join(PROJECT_DIR, "outputs", "test_output_crf28.mp4")
    print(f"\n[Test 4] Executing compression with CRF 28, downscaling to 480p...")
    res28 = compress_video(
        input_path=test_input,
        output_path=test_output_crf28,
        crf=28,
        preset="fast",
        target_resolution="480p",
        preserve_audio=True
    )
    assert res28["success"] is True, "Compression reported failure"
    assert os.path.isfile(test_output_crf28), "Output file was not created"
    assert res28["compressed_size_bytes"] > 0, "Compressed size must be > 0"
    print(f"  --> PASS: Compression completed in {res28['encoding_time_seconds']}s")

    # 5. Mathematical Formula Validations
    print("\n[Test 5] Validating compression formulas and calculations...")
    orig_sz = res28["original_size_bytes"]
    comp_sz = res28["compressed_size_bytes"]
    expected_saved = orig_sz - comp_sz
    expected_reduction = round(((orig_sz - comp_sz) / orig_sz) * 100.0, 2)
    expected_ratio = round(orig_sz / comp_sz, 2)

    assert res28["storage_saved_bytes"] == expected_saved, "Storage saved formula error"
    assert res28["storage_reduction_pct"] == expected_reduction, "Storage reduction % formula error"
    assert res28["compression_ratio"] == expected_ratio, "Compression ratio formula error"
    print(f"  Original Size      : {res28['original_size_formatted']}")
    print(f"  Compressed Size    : {res28['compressed_size_formatted']}")
    print(f"  Storage Saved      : {res28['storage_saved_formatted']}")
    print(f"  Storage Reduction  : {res28['storage_reduction_pct']}%")
    print(f"  Compression Ratio  : {res28['compression_ratio']}:1")
    print(f"  Encoding Time      : {res28['encoding_time_seconds']} seconds")
    print("  --> PASS: All formulas strictly validated against ground truth")

    # 6. Compressed Video Inspection (Resolution & Codec Verification)
    print("\n[Test 6] Inspecting output stream properties with FFprobe...")
    comp_meta28 = res28["compressed_metadata"]
    assert comp_meta28["height"] == 480, f"Expected height 480, got {comp_meta28['height']}"
    assert "H264" in comp_meta28["video_codec"], f"Expected H264 codec, got {comp_meta28['video_codec']}"
    assert comp_meta28["has_audio"] is True, "Expected preserved audio"
    print(f"  --> PASS: Compressed stream valid: {comp_meta28['resolution']}, Codec: {comp_meta28['video_codec']}")

    # 7. Rate-Distortion Scaling Test (CRF 28 vs CRF 36)
    test_output_crf36 = os.path.join(PROJECT_DIR, "outputs", "test_output_crf36.mp4")
    print("\n[Test 7] Testing Rate-Distortion property (CRF 36 should compress more than CRF 28)...")
    res36 = compress_video(
        input_path=test_input,
        output_path=test_output_crf36,
        crf=36,
        preset="fast",
        target_resolution="480p",
        preserve_audio=True
    )
    assert res36["compressed_size_bytes"] < res28["compressed_size_bytes"], (
        f"CRF 36 size ({res36['compressed_size_bytes']}) should be strictly smaller than "
        f"CRF 28 size ({res28['compressed_size_bytes']})"
    )
    print(f"  CRF 28 Size: {res28['compressed_size_formatted']}")
    print(f"  CRF 36 Size: {res36['compressed_size_formatted']} (Smaller as expected by rate-distortion theory)")
    print("  --> PASS: Rate-distortion scaling confirmed.")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! The Video Compression project is verified.")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
