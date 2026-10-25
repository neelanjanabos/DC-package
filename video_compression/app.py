"""
Video Compression
A Streamlit web application for H.264/MPEG-4 AVC video compression.
College Data Compression Project.
"""

import os
import sys
import time
import shutil
import streamlit as st

# Ensure local imports work regardless of working directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from video_metadata import extract_metadata, format_bytes
from compressor import compress_video

# Page configuration
st.set_page_config(
    page_title="Video Compression",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom styling for a clean, attractive student & evaluator UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stDownloadButton button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        width: 100%;
        padding: 0.6rem;
    }
    /* Compact, centered, and responsive video previews */
    div[data-testid="stVideo"],
    div.stVideo {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin: 0.5rem auto !important;
    }
    div[data-testid="stVideo"] video,
    div.stVideo video,
    video.stVideo,
    video {
        max-width: min(600px, 100%) !important;
        max-height: 300px !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
        border-radius: 6px;
    }
    /* Compact expander content padding */
    div[data-testid="stExpander"] div[role="region"] {
        padding: 0.5rem 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Application Directories
UPLOADS_DIR = os.path.join(CURRENT_DIR, "uploads")
OUTPUTS_DIR = os.path.join(CURRENT_DIR, "outputs")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ---------------------------------------------------------
# Main Interface
# ---------------------------------------------------------
st.markdown('<div class="main-header">Video Compression</div>', unsafe_allow_html=True)

# Step 1: Upload Video
st.header("1. Upload Video")
uploaded_file = st.file_uploader(
    "Choose a video file to compress",
    type=["mp4", "mkv", "mov", "avi", "webm", "flv", "ts", "m4v"],
    help="Supports standard formats handled by FFmpeg and HTML5 video playback."
)

if uploaded_file is not None:
    # Save uploaded file to uploads directory
    input_filename = uploaded_file.name
    input_path = os.path.join(UPLOADS_DIR, input_filename)

    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract metadata using FFprobe
    try:
        orig_meta = extract_metadata(input_path)
    except Exception as e:
        st.error(f"Error inspecting video: {e}")
        st.stop()

    # Display original metadata in 5 clear metric cards
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    with col_a:
        st.metric("Original Size", orig_meta["file_size_formatted"])
    with col_b:
        st.metric("Duration", orig_meta["duration_formatted"])
    with col_c:
        st.metric("Resolution", orig_meta["resolution"])
    with col_d:
        st.metric("Frame Rate", f"{orig_meta['frame_rate']} fps")
    with col_e:
        st.metric("Video Codec", orig_meta["video_codec"])

    # Original Video Preview
    with st.expander("Original Video Preview", expanded=True):
        st.video(input_path)

    st.markdown("---")

    # Step 2: Compression Settings
    st.header("2. Compression Settings")
    st.markdown("Configure encoding parameters according to the rate-distortion trade-offs of MPEG-4 AVC.")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        crf_val = st.slider(
            "Constant Rate Factor (CRF)",
            min_value=18,
            max_value=51,
            value=28,
            step=1,
            help=(
                "Lower CRF gives higher visual quality and larger files. "
                "Higher CRF gives smaller files and lower visual quality. "
                "Default is 28 (recommended for web video compression)."
            )
        )
        st.info(
            f"**Current CRF = {crf_val}**: "
            + ("High Quality / Light Compression (Larger file)" if crf_val <= 23 else
               "Balanced Compression & Quality (Default)" if crf_val <= 30 else
               "Aggressive Compression (Substantial size reduction, visible artifacts)")
        )

        preset_val = st.selectbox(
            "Encoding Speed (Preset)",
            options=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"],
            index=5,
            help="Slower presets invest more computational time in motion estimation to achieve better compression efficiency."
        )

    with col_s2:
        resolution_options = [
            "Original (Maintain source resolution)",
            "1080p (1920x1080)",
            "720p (1280x720)",
            "480p (854x480)",
            "360p (640x360)"
        ]
        target_res = st.selectbox(
            "Resolution Scaling",
            options=resolution_options,
            index=0,
            help="Downscaling video resolution reduces the total pixel count per frame, significantly cutting storage requirements."
        )

        preserve_audio = st.checkbox(
            "Preserve Audio",
            value=True,
            help="Keep the audio track encoded in standard AAC format (128 kbps). Uncheck to strip audio completely."
        )

        st.text_input("Output Format", value="MP4 (MPEG-4 Part 10 AVC)", disabled=True)

    st.markdown("---")

    # Step 3: Compress Video Action
    st.header("3. Compress Video")
    
    compress_clicked = st.button("Compress Video", type="primary", use_container_width=True)

    # State key for preserving result across UI re-renders
    result_key = f"result_{input_filename}_{crf_val}_{target_res}_{preset_val}_{preserve_audio}"

    if compress_clicked:
        # Prepare output filename and path
        base_name, _ = os.path.splitext(input_filename)
        output_filename = f"{base_name}_crf{crf_val}_compressed.mp4"
        output_path = os.path.join(OUTPUTS_DIR, output_filename)

        with st.spinner("Compressing video using H.264/AVC (libx264)... Please wait."):
            try:
                compression_result = compress_video(
                    input_path=input_path,
                    output_path=output_path,
                    crf=crf_val,
                    preset=preset_val,
                    target_resolution=target_res,
                    preserve_audio=preserve_audio
                )
                st.session_state[result_key] = compression_result
                st.session_state["latest_result_key"] = result_key
                st.success(f"Compression completed in {compression_result['encoding_time_seconds']} seconds!")
            except Exception as e:
                st.error(f"Compression failed: {e}")

    # Step 4: Results & Comparison
    if st.session_state.get("latest_result_key") and st.session_state["latest_result_key"] in st.session_state:
        res = st.session_state[st.session_state["latest_result_key"]]

        st.markdown("---")
        st.header("4. Results and Analysis")

        # Metric cards
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)

        with m_col1:
            st.metric("Original Size", res["original_size_formatted"])
        with m_col2:
            st.metric("Compressed Size", res["compressed_size_formatted"])
        with m_col3:
            saved_label = res["storage_saved_formatted"]
            st.metric("Storage Saved", saved_label)
        with m_col4:
            st.metric("Storage Reduction", f"{res['storage_reduction_pct']}%")
        with m_col5:
            st.metric("Compression Ratio", f"{res['compression_ratio']}:1")
        with m_col6:
            st.metric("Encoding Time", f"{res['encoding_time_seconds']} s")

        # Honest reporting for size changes
        if res["is_size_increased"]:
            st.warning(
                f"**Note on Negative Reduction**: The compressed file size ({res['compressed_size_formatted']}) "
                f"is larger than the original ({res['original_size_formatted']}). "
                "This occurs when re-encoding an already heavily-compressed source at a very low CRF (high quality target) "
                "or when transcoding overhead exceeds savings on short/low-entropy clips. This is an honest reflection of "
                "actual measurements as studied in rate-distortion theory."
            )
        else:
            st.success(
                f"Successfully reduced file size by **{res['storage_reduction_pct']}%** "
                f"({res['storage_saved_formatted']} saved) at a Compression Ratio of **{res['compression_ratio']}:1**."
            )

        # Technical Output Properties Table
        st.subheader("Stream Properties Comparison")
        comp_meta = res["compressed_metadata"]

        comp_data = {
            "Property": ["File Size", "Resolution", "Video Codec", "Bitrate", "Frame Rate", "Audio Codec"],
            "Original Video": [
                res["original_size_formatted"],
                res["original_metadata"]["resolution"],
                res["original_metadata"]["video_codec"],
                f"{res['original_metadata']['bitrate_kbps']} kbps",
                f"{res['original_metadata']['frame_rate']} fps",
                res["original_metadata"]["audio_codec"] or "None"
            ],
            "Compressed Video": [
                res["compressed_size_formatted"],
                comp_meta["resolution"],
                comp_meta["video_codec"],
                f"{comp_meta['bitrate_kbps']} kbps",
                f"{comp_meta['frame_rate']} fps",
                comp_meta["audio_codec"] or "None"
            ]
        }
        st.table(comp_data)

        # Previews
        st.subheader("Side-by-Side Video Previews")
        prev_col1, prev_col2 = st.columns(2)

        with prev_col1:
            st.markdown(f"**Original Video** (`{res['original_size_formatted']}`)")
            st.video(res["input_path"])

        with prev_col2:
            st.markdown(f"**Compressed Video (CRF {res['crf']})** (`{res['compressed_size_formatted']}`)")
            st.video(res["output_path"])

        # Download compressed video
        st.subheader("5. Download Compressed Video")
        with open(res["output_path"], "rb") as comp_file:
            comp_bytes = comp_file.read()

        st.download_button(
            label=f"⬇️ Download Compressed Video ({res['compressed_size_formatted']})",
            data=comp_bytes,
            file_name=os.path.basename(res["output_path"]),
            mime="video/mp4"
        )

        with st.expander("Underlying FFmpeg Command"):
            st.code(res["command_executed"], language="bash")
            st.caption(
                "Notice the flags: `-c:v libx264` specifies the MPEG-4 AVC encoder, "
                "`-crf` defines the rate-distortion factor, `-pix_fmt yuv420p` ensures broad compatibility, "
                "and `-movflags +faststart` enables progressive playback."
            )

else:
    st.info("Please upload a video file above to begin compression.")
