# 🎬 FFmpeg Sequence Tools for Windows

Right-click context menu tools for converting between **video files** and **image sequences** using [FFmpeg](https://ffmpeg.org/).

![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?logo=windows)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-required-007808?logo=ffmpeg)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

### 🎥 → 🖼️ Video to Image Sequence
- Convert any video file to numbered PNG frames (`Name.0001.png`, `Name.0002.png`, ...)
- **Single file** — right-click a video
- **Batch mode** — right-click a folder to convert all videos
- Automatically skips already-converted videos
- Real-time progress bar with frame counter

### 🖼️ → 🎥 Image Sequence to MP4
- Convert numbered image sequences back to MP4 video
- Auto-detects sequence naming pattern (`Name.####.ext`)
- Configurable **FPS**, **quality (CRF)**, and **encoder preset**
- Right-click any image file or a folder of images
- Output MP4 is placed next to the folder, not inside it

Both tools feature a clean **dark-themed GUI** with progress tracking.

---

## 📋 Requirements

1. **Windows 10 or 11**
2. **Python 3.10+** — [Download from python.org](https://www.python.org/downloads/) or the Microsoft Store
3. **FFmpeg** — must be on your system PATH
   - [Download FFmpeg](https://www.gyan.dev/ffmpeg/builds/) (get the "essentials" build)
   - Extract and add the `bin` folder to your PATH

### Verify FFmpeg is installed:
```
ffmpeg -version
ffprobe -version
```

---

## 🚀 Installation

### Quick Install (Recommended)

1. **Clone or download** this repository:
   ```
   git clone https://github.com/bwardcg/ffmpeg-sequence-tools.git
   ```
   Or click **Code → Download ZIP** and extract anywhere.

2. **Run the installer** (right-click → Run as Administrator):
   ```
   install.bat
   ```
   This will register both tools in your Windows right-click context menu.

### Manual Install

If you prefer, you can install each tool separately:

```powershell
# Install Video → Image Sequence context menu
python install_context_menu.py install

# Install Image Sequence → MP4 context menu
python install_images_to_video_menu.py install
```

Both scripts auto-elevate to Administrator.

---

## 📖 Usage

### Video to Image Sequence

1. **Right-click** a video file (`.mp4`, `.mov`, `.avi`, `.mkv`, etc.)
2. Select **"Convert to Image Sequence"**
3. A progress window appears — frames are saved as `VideoName.0001.png` etc.

For **batch conversion**, right-click a **folder** containing videos and select **"Batch Convert Videos to Image Sequences"**.

### Image Sequence to MP4

1. **Right-click** any image file from a sequence (`.png`, `.jpg`, `.exr`, `.tga`, etc.)
2. Select **"Create MP4 from Image Sequence"**
3. Adjust FPS, quality, and output path, then click **Convert**

You can also right-click a **folder** containing an image sequence.

> **Windows 11 Note:** You may need to click **"Show more options"** to see the context menu entries.

---

## 🗑️ Uninstall

Run the uninstaller:
```
uninstall.bat
```

Or manually:
```powershell
python install_context_menu.py uninstall
python install_images_to_video_menu.py uninstall
```

---

## ⚙️ Configuration

### Video to Image Sequence
Edit the constants at the top of `video_to_sequence.py`:
| Setting | Default | Description |
|---------|---------|-------------|
| `OUTPUT_FORMAT` | `"png"` | Output image format (`png`, `jpg`) |
| `JPEG_QUALITY` | `2` | JPEG quality (1=best, 31=worst) |
| `PADDING` | `4` | Frame number padding (4 → `0001`) |

### Image Sequence to MP4
Settings are adjustable in the GUI, with defaults in `images_to_video.py`:
| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_FPS` | `24` | Frames per second |
| `DEFAULT_CRF` | `18` | Quality (0=lossless, 51=worst) |
| `DEFAULT_PRESET` | `"medium"` | x264 speed/quality tradeoff |

---

## 📁 File Structure

```
ffmpeg-sequence-tools/
├── video_to_sequence.py           # Video → image sequence converter
├── images_to_video.py             # Image sequence → MP4 converter
├── install_context_menu.py        # Installer for video tool menu
├── install_images_to_video_menu.py # Installer for image tool menu
├── install.bat                    # One-click install (run as admin)
├── uninstall.bat                  # One-click uninstall
├── LICENSE
└── README.md
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
