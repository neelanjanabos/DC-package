# Video Compression

A working Data Compression college engineering project that demonstrates video compression using the **H.264 / MPEG-4 Part 10 Advanced Video Coding (AVC)** standard, powered by **Python**, **Streamlit**, and **FFmpeg** (`libx264`).

---

## 1. Abstract

Digital video accounts for more than 80% of global internet traffic and requires immense storage capacity in uncompressed or lightly compressed formats. Video compression techniques exploit spatial redundancy (redundancy within a single frame) and temporal redundancy (redundancy across successive frames) to dramatically reduce file sizes while preserving acceptable perceptual fidelity.

This project implements an interactive, reproducible video compression application based on the foundational research paper *"Overview of the H.264/AVC Video Coding Standard"* by Thomas Wiegand et al. (IEEE TCSVT, 2003). By wrapping the industry-standard `libx264` encoder within a clean Python and Streamlit web interface, the system allows students and evaluators to compress videos, analyze rate-distortion trade-offs via Constant Rate Factor (CRF) scaling, test spatial resolution reduction, and measure actual storage savings, compression ratios, and encoding times with genuine hardware execution.

---

## 2. Objectives

1. **Practical Demonstration of Video Compression**: Build an end-to-end, functional system that compresses actual video files rather than simulating formulas.
2. **Implementation of MPEG-4 Part 10 AVC**: Apply genuine H.264/AVC compression using the `libx264` library via safe subprocess orchestration with FFmpeg.
3. **Exploration of Rate-Distortion Trade-offs**: Enable users to experiment with Constant Rate Factor (CRF) and resolution scaling, analyzing their impact on file size and visual quality.
4. **Rigorous Metric Evaluation**: Compute and display real-world performance metrics including Compression Ratio, Storage Saved, Percentage Storage Reduction, and Encoding Time.
5. **Academic Grounding**: Relate system components directly to syllabus topics—motion compensation, intra/inter-prediction, discrete cosine transform (DCT), and quantization.

---

## 3. Research Paper Reference

This project is grounded in the landmark peer-reviewed research paper:

- **Paper Title**: *Overview of the H.264/AVC Video Coding Standard*
- **Authors**: Thomas Wiegand, Gary J. Sullivan, Gisle Bjøntegaard, and Ajay Luthra
- **Publication**: *IEEE Transactions on Circuits and Systems for Video Technology (TCSVT)*, Vol. 13, No. 7, pp. 560–576, July 2003.
- **DOI**: [10.1109/TCSVT.2003.815165](https://doi.org/10.1109/TCSVT.2003.815165)
- **Standard Details**: Jointly formulated by ITU-T VCEG and ISO/IEC MPEG as ITU-T H.264 and ISO/IEC 14496-10 (MPEG-4 Part 10 AVC).

For in-depth analysis of the paper's methodology, architecture, and empirical findings, refer to [research_paper.md](research_paper.md).

---

## 4. Theory and Syllabus Relevance

### 4.1 MPEG-4 Part 10 AVC (H.264)
H.264 is also designated internationally as **MPEG-4 Part 10 AVC**. Developed by the Joint Video Team (JVT), it delivered a breakthrough **50% or greater bit-rate savings** compared to prior standards (MPEG-2 Video and MPEG-4 Part 2) at equivalent perceptual quality.

### 4.2 Motion Compensation (Temporal Redundancy)
Consecutive frames in video streams have high correlation. H.264 divides video into three primary frame types:
- **I-Frames (Intra-coded)**: Coded independently using spatial prediction from neighboring pixels.
- **P-Frames (Predicted)**: Coded with forward prediction using motion vectors referenced to previous pictures.
- **B-Frames (Bi-directionally Predicted)**: Coded with weighted predictions from past and future pictures.

Unlike MPEG-2's rigid $16\times16$ macroblock motion vectors, H.264 employs **variable block-size motion estimation** ($16\times16$, $16\times8$, $8\times16$, $8\times8$, $8\times4$, $4\times8$, $4\times4$) combined with **quarter-pixel (1/4-pel) motion vector precision**. This allows the encoder to isolate moving objects with high precision, transmitting only small residual prediction errors.

### 4.3 Integer Discrete Cosine Transform (DCT) & Quantization
The residual differences are transformed using an exact $4\times4$ integer discrete cosine transform. Scalar quantization with a Quantization Parameter ($QP$) ranging from 0 to 51 scales the coefficients. In x264, the **Constant Rate Factor (CRF)** dynamically adjusts $QP$ during encoding to optimize perceptual quality: high-motion areas (where human eyes are less sensitive to high-frequency artifacts) receive higher quantization, whereas clean, static areas receive lower quantization.

---

## 5. Mathematical Formulas

The application evaluates compression performance using these exact formulas:

### 5.1 Compression Ratio
$$\text{Compression Ratio} = \frac{\text{Original File Size (bytes)}}{\text{Compressed File Size (bytes)}}$$
A ratio greater than $1.0$ indicates file size reduction (e.g., $3.5:1$ indicates the original was $3.5\times$ larger).

### 5.2 Storage Saved
$$\text{Storage Saved (bytes)} = \text{Original File Size (bytes)} - \text{Compressed File Size (bytes)}$$

### 5.3 Storage Reduction (%)
$$\text{Storage Reduction (\%)} = \left( \frac{\text{Original File Size} - \text{Compressed File Size}}{\text{Original File Size}} \right) \times 100$$

### 5.4 Encoding Time
$$\text{Encoding Time (seconds)} = t_{\text{end}} - t_{\text{start}}$$
Measured with high-precision monotonic timers (`time.perf_counter()`) encompassing the full FFmpeg encoding execution.

*Honest Reporting Note*: If an already heavily-compressed video is re-encoded at a very low CRF (e.g., CRF 18), the compressed output may be larger than the input. The system reports negative savings and ratios $<1.0$ honestly, reflecting real rate-distortion mechanics.

---

## 6. System Architecture & Workflow

The user workflow consists of five distinct steps:

```
[Upload Video] ──► [Select Quality] ──► [Compress Video] ──► [Compare Results] ──► [Download Video]
       │                   │                   │                    │                   │
  Extract Info        Set CRF & Res        Run FFmpeg           Display Metrics       Save Output
   (FFprobe)         (libx264 flags)     with Subprocess     & Side-by-Side Video    (.mp4 file)
```

1. **Upload Video**: Upload an input video (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`). The system uses `ffprobe` to inspect technical metadata (file size, duration, resolution, frame rate, audio/video codecs).
2. **Select Quality**: Adjust the CRF slider (18–51, default 28), choose an encoding speed preset, select optional downscaling (1080p, 720p, 480p, 360p), and configure audio preservation.
3. **Compress Video**: Execute compression using FFmpeg and `libx264` via secure Python subprocess calls with `-pix_fmt yuv420p` and `-movflags +faststart`.
4. **Compare Results**: Inspect real measured metrics (Compression Ratio, Storage Saved, Percentage Reduction, Encoding Time) and preview original vs. compressed video side-by-side.
5. **Download Compressed Video**: Save the resulting optimized MP4 file directly to the local machine.

---

## 7. Project Structure

```
video_compression/
├── app.py               # Streamlit frontend user interface
├── compressor.py        # FFmpeg & libx264 video compression engine
├── video_metadata.py    # FFprobe metadata extraction utility
├── test_compression.py  # Automated test suite with synthetic video verification
├── research_paper.md    # Detailed academic review of Wiegand et al. (2003)
├── README.md            # Complete project documentation
├── requirements.txt     # Python package dependencies
├── .gitignore           # Git ignore file for temp files and video caches
├── uploads/             # Directory storing uploaded input videos (.gitkeep)
└── outputs/             # Directory storing compressed output videos (.gitkeep)
```

---

## 8. Requirements and Installation

### 8.1 Prerequisites
- **Python**: 3.9 or higher
- **FFmpeg & FFprobe**: Must be installed with the `libx264` encoder enabled

### 8.2 Installation Instructions

#### Windows
1. Install FFmpeg using Windows Package Manager (`winget`):
   ```powershell
   winget install --id Gyan.FFmpeg.Essentials
   ```
2. Verify installation in PowerShell:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```
3. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg python3-pip
pip install -r requirements.txt
```

#### macOS (Homebrew)
```bash
brew install ffmpeg
pip install -r requirements.txt
```

---

## 9. Execution Instructions

1. Navigate to the project directory:
   ```bash
   cd video_compression
   ```
2. Launch the Streamlit application:
   ```bash
   streamlit run app.py
   ```
3. The application will open automatically in your browser at:
   ```
   http://localhost:8501
   ```

---

## 10. Automated Testing

The project includes an automated test script (`test_compression.py`) that generates a synthetic test video using FFmpeg and validates metadata extraction, compression execution, mathematical calculations, and output integrity.

To execute the test suite:
```bash
python test_compression.py
```

### Expected Test Output
- Generates a synthetic 5-second video with moving bars, timestamps, and sine audio.
- Extracts and validates original video metadata with FFprobe.
- Executes compression at CRF 28 and downscales to 480p.
- Verifies mathematical formulas:
  - $\text{Compression Ratio} = \frac{\text{Original Size}}{\text{Compressed Size}}$
  - $\text{Storage Saved} = \text{Original Size} - \text{Compressed Size}$
  - $\text{Reduction \%} = \frac{\text{Storage Saved}}{\text{Original Size}} \times 100$
- Confirms the compressed output file exists, is valid H.264/AAC, and is playable.

---

## 11. Limitations

1. **Lossy Compression Nature**: H.264 with non-zero CRF is lossy; high CRF values ($\ge 35$) produce visible blocking, blurring, and banding artifacts.
2. **Computational Overhead**: Higher encoding presets (`slow`, `veryslow`) significantly increase encoding time due to multi-pass motion estimation and exhaustive partition evaluations.
3. **Pre-Compressed Sources**: If an uploaded video has already been heavily compressed with aggressive settings, re-compressing it may yield little to no additional savings, or may even increase file size due to transcoding overhead.
4. **Single-Node Execution**: Current processing runs synchronously via local subprocess calls; large 4K files may take noticeable time depending on CPU capabilities.

---

## 12. Future Enhancements

1. **Next-Generation Codecs**: Extend support to H.265/HEVC (`libx265`) and AV1 (`libsvtav1`) to benchmark inter-generational compression efficiency gains.
2. **Objective Quality Metrics**: Integrate automated PSNR (Peak Signal-to-Noise Ratio) and SSIM (Structural Similarity Index) calculations directly into the UI.
3. **Bitrate-Constrained 2-Pass Encoding**: Add a target file size mode utilizing 2-pass average bitrate (ABR) encoding.
4. **Hardware Acceleration**: Enable GPU-accelerated encoding via NVENC (NVIDIA), QSV (Intel), or VideoToolbox (Apple).
