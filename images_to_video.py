"""
Image Sequence to MP4 Video Converter - uses ffmpeg.
Right-click context menu integration for Windows 11.
Usage:
    python images_to_video.py "<path_to_image_file>"
    python images_to_video.py "<path_to_directory>"

When invoked on a single image file, it auto-detects the sequence in the
same directory based on the naming pattern (Name.####.ext) and converts
all frames into an MP4 video.
"""
import subprocess, sys, os, json, re, threading, glob, time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_FPS = 24
DEFAULT_CRF = 18          # quality: 0 = lossless, 51 = worst; ~18 is visually lossless
DEFAULT_PRESET = "medium"  # x264 speed preset
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".exr", ".tga", ".tif", ".tiff", ".bmp", ".dpx"}

# ── Helpers ──────────────────────────────────────────────────────────────────

_SEQ_PATTERN = re.compile(
    r'^(?P<base>.+?)[._](?P<num>\d{2,8})(?P<ext>\.\w+)$'
)

def detect_sequence(seed_path):
    """Given one image file, figure out the full sequence.

    Returns (directory, base_name, extension, padding, first_frame, last_frame, count)
    or None if no sequence detected.
    """
    directory = os.path.dirname(seed_path)
    filename = os.path.basename(seed_path)
    m = _SEQ_PATTERN.match(filename)
    if not m:
        return None

    base = m.group("base")
    ext = m.group("ext").lower()
    padding = len(m.group("num"))

    # gather all files that match this pattern
    frames = []
    for f in os.listdir(directory):
        fm = _SEQ_PATTERN.match(f)
        if fm and fm.group("base") == base and fm.group("ext").lower() == ext and len(fm.group("num")) == padding:
            frames.append(int(fm.group("num")))

    if not frames:
        return None

    frames.sort()
    return (directory, base, ext, padding, frames[0], frames[-1], len(frames))


def detect_sequence_in_directory(directory):
    """Scan a directory and return info for the largest image sequence found."""
    sequences = {}  # key = (base, ext, padding) -> list of frame numbers
    for f in os.listdir(directory):
        if not os.path.isfile(os.path.join(directory, f)):
            continue
        m = _SEQ_PATTERN.match(f)
        if not m:
            continue
        ext = m.group("ext").lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        key = (m.group("base"), ext, len(m.group("num")))
        sequences.setdefault(key, []).append(int(m.group("num")))

    if not sequences:
        return None

    # pick the sequence with the most frames
    best_key = max(sequences, key=lambda k: len(sequences[k]))
    base, ext, padding = best_key
    frames = sorted(sequences[best_key])
    return (directory, base, ext, padding, frames[0], frames[-1], len(frames))


def build_ffmpeg_cmd(directory, base, ext, padding, fps, crf, preset,
                     first_frame, output_path):
    """Build the ffmpeg command list."""
    # ffmpeg input pattern:  Name.%04d.png
    input_pattern = os.path.join(directory, f"{base}.%0{padding}d{ext}")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-start_number", str(first_frame),
        "-i", input_pattern,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p",   # broad compatibility
        "-movflags", "+faststart",
        output_path
    ]
    return cmd


# ── GUI ──────────────────────────────────────────────────────────────────────

class ImagesToVideoGUI:
    """GUI for converting an image sequence to MP4."""

    BG       = "#1e1e2e"
    FG       = "#cdd6f4"
    FG_DIM   = "#a6adc8"
    FG_MUTED = "#6c7086"
    SURFACE  = "#313244"
    ACCENT   = "#89b4fa"
    GREEN    = "#a6e3a1"
    RED      = "#f38ba8"
    BTN_BG   = "#45475a"

    def __init__(self, seq_info, output_dir=None):
        self.directory, self.base, self.ext, self.padding, \
            self.first, self.last, self.count = seq_info
        # output_dir controls where the .mp4 is saved;
        # defaults to the same directory as the images
        self.output_dir = output_dir or self.directory
        self.cancelled = False

        self.root = tk.Tk()
        self.root.title("Image Sequence → MP4")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)
        self.root.attributes("-topmost", True)
        w, h = 540, 420
        sx = (self.root.winfo_screenwidth() - w) // 2
        sy = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Horizontal.TProgressbar", troughcolor=self.SURFACE,
            background=self.ACCENT, darkcolor=self.ACCENT, lightcolor=self.ACCENT,
            bordercolor=self.BG, thickness=18)

        px = {"padx": 20}

        # ── Title ────────────────────────────────────────────────────
        tk.Label(self.root, text="Image Sequence → MP4",
            font=("Segoe UI", 14, "bold"), fg=self.FG, bg=self.BG
        ).pack(pady=(18, 4), **px, anchor="w")

        # ── Sequence info ────────────────────────────────────────────
        seq_label = f"{self.base}.{'#' * self.padding}{self.ext}"
        tk.Label(self.root, text=f"Sequence:  {seq_label}",
            font=("Segoe UI", 10), fg=self.FG_DIM, bg=self.BG
        ).pack(pady=(0, 2), **px, anchor="w")

        tk.Label(self.root,
            text=f"Frames:  {self.first} – {self.last}  ({self.count:,} files)",
            font=("Segoe UI", 10), fg=self.FG_DIM, bg=self.BG
        ).pack(pady=(0, 2), **px, anchor="w")

        dir_short = self.directory
        if len(dir_short) > 55:
            dir_short = "..." + dir_short[-52:]
        tk.Label(self.root, text=f"Folder:  {dir_short}",
            font=("Segoe UI", 9), fg=self.FG_MUTED, bg=self.BG
        ).pack(pady=(0, 12), **px, anchor="w")

        # ── Settings row ─────────────────────────────────────────────
        settings_frame = tk.Frame(self.root, bg=self.BG)
        settings_frame.pack(pady=(0, 6), **px, anchor="w")

        tk.Label(settings_frame, text="FPS:", font=("Segoe UI", 10),
            fg=self.FG, bg=self.BG).pack(side="left")
        self.fps_var = tk.StringVar(value=str(DEFAULT_FPS))
        fps_entry = tk.Entry(settings_frame, textvariable=self.fps_var,
            width=5, font=("Segoe UI", 10), bg=self.SURFACE, fg=self.FG,
            insertbackground=self.FG, relief="flat", bd=2)
        fps_entry.pack(side="left", padx=(4, 16))

        tk.Label(settings_frame, text="Quality (CRF):", font=("Segoe UI", 10),
            fg=self.FG, bg=self.BG).pack(side="left")
        self.crf_var = tk.StringVar(value=str(DEFAULT_CRF))
        crf_entry = tk.Entry(settings_frame, textvariable=self.crf_var,
            width=4, font=("Segoe UI", 10), bg=self.SURFACE, fg=self.FG,
            insertbackground=self.FG, relief="flat", bd=2)
        crf_entry.pack(side="left", padx=(4, 16))

        tk.Label(settings_frame, text="Preset:", font=("Segoe UI", 10),
            fg=self.FG, bg=self.BG).pack(side="left")
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        preset_menu = ttk.Combobox(settings_frame, textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast",
                    "medium", "slow", "slower", "veryslow"],
            width=10, state="readonly", font=("Segoe UI", 9))
        preset_menu.pack(side="left", padx=(4, 0))

        # ── Output filename ──────────────────────────────────────────
        out_frame = tk.Frame(self.root, bg=self.BG)
        out_frame.pack(pady=(6, 12), **px, fill="x")

        tk.Label(out_frame, text="Output:", font=("Segoe UI", 10),
            fg=self.FG, bg=self.BG).pack(side="left")

        default_output = os.path.join(self.output_dir, f"{self.base}.mp4")
        self.output_var = tk.StringVar(value=default_output)
        out_entry = tk.Entry(out_frame, textvariable=self.output_var,
            font=("Segoe UI", 9), bg=self.SURFACE, fg=self.FG,
            insertbackground=self.FG, relief="flat", bd=2)
        out_entry.pack(side="left", padx=(6, 4), fill="x", expand=True)

        tk.Button(out_frame, text="...", width=3,
            font=("Segoe UI", 9), fg=self.FG, bg=self.BTN_BG,
            activebackground=self.SURFACE, relief="flat", cursor="hand2",
            command=self._browse_output).pack(side="left")

        # ── Progress ─────────────────────────────────────────────────
        self.progress = ttk.Progressbar(self.root, length=490, mode="determinate",
            style="C.Horizontal.TProgressbar")
        self.progress.pack(pady=(0, 6), **px)

        self.status_label = tk.Label(self.root, text="Ready",
            font=("Segoe UI", 10), fg=self.FG, bg=self.BG)
        self.status_label.pack(pady=(0, 14), **px, anchor="w")

        # ── Buttons ──────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=self.BG)
        btn_frame.pack(pady=(0, 14))

        self.convert_btn = tk.Button(btn_frame, text="Convert", width=12,
            font=("Segoe UI", 10, "bold"), fg=self.BG, bg=self.GREEN,
            activebackground="#94e2d5", relief="flat", cursor="hand2",
            command=self._start_convert)
        self.convert_btn.pack(side="left", padx=6)

        self.cancel_btn = tk.Button(btn_frame, text="Cancel", width=10,
            font=("Segoe UI", 10), fg=self.FG, bg=self.RED,
            activebackground="#eba0ac", relief="flat", cursor="hand2",
            command=self._cancel)
        self.cancel_btn.pack(side="left", padx=6)

        self.root.protocol("WM_DELETE_WINDOW", self._cancel)
        self.root.mainloop()

    # ── UI helpers ───────────────────────────────────────────────────

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save MP4 As",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All files", "*.*")],
            initialdir=self.output_dir,
            initialfile=f"{self.base}.mp4"
        )
        if path:
            self.output_var.set(path)

    def _cancel(self):
        self.cancelled = True
        try:
            self.root.destroy()
        except:
            pass

    def _ui(self, fn, *a):
        try:
            self.root.after(0, fn, *a)
        except:
            pass

    def _set_status(self, t):
        self.status_label.config(text=t)

    def _set_pct(self, v):
        self.progress["value"] = v

    # ── Conversion ───────────────────────────────────────────────────

    def _start_convert(self):
        # Validate inputs
        try:
            fps = int(self.fps_var.get())
            if fps < 1 or fps > 240:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid FPS", "FPS must be an integer between 1 and 240.")
            return

        try:
            crf = int(self.crf_var.get())
            if crf < 0 or crf > 51:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid CRF", "CRF must be an integer between 0 and 51.")
            return

        preset = self.preset_var.get()
        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showerror("No Output", "Please specify an output file path.")
            return

        # Warn if file exists
        if os.path.isfile(output_path):
            if not messagebox.askyesno("Overwrite?",
                    f"File already exists:\n{os.path.basename(output_path)}\n\nOverwrite?"):
                return

        # Disable convert button, start worker
        self.convert_btn.config(state="disabled", bg=self.BTN_BG)
        self._ui(self._set_status, "Converting...")
        threading.Thread(target=self._run_convert,
            args=(fps, crf, preset, output_path), daemon=True).start()

    def _run_convert(self, fps, crf, preset, output_path):
        try:
            cmd = build_ffmpeg_cmd(
                self.directory, self.base, self.ext, self.padding,
                fps, crf, preset, self.first, output_path
            )

            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0

            proc = subprocess.Popen(cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                startupinfo=si)

            # Read stderr for progress (ffmpeg writes progress to stderr)
            # We'll parse "frame=  123" from ffmpeg output
            frame_re = re.compile(r'frame=\s*(\d+)')
            total_expected = self.count

            # Read output in a thread to avoid blocking
            stderr_lines = []
            def read_stderr():
                for line in proc.stderr:
                    stderr_lines.append(line)

            reader = threading.Thread(target=read_stderr, daemon=True)
            reader.start()

            while proc.poll() is None:
                if self.cancelled:
                    proc.terminate()
                    return

                # Check last few lines for frame count
                current_frame = 0
                for line in stderr_lines[-5:]:
                    text = line.decode('utf-8', errors='replace')
                    m = frame_re.search(text)
                    if m:
                        current_frame = int(m.group(1))

                if total_expected > 0 and current_frame > 0:
                    pct = min(99.0, current_frame / total_expected * 100)
                    self._ui(self._set_pct, pct)
                    self._ui(self._set_status,
                        f"Encoding...  frame {current_frame:,} / {total_expected:,}")
                time.sleep(0.5)

            reader.join(timeout=2)

            if self.cancelled:
                return

            if proc.returncode == 0:
                # Get file size
                try:
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    size_str = f"  ({size_mb:.1f} MB)"
                except:
                    size_str = ""

                self._ui(self._set_pct, 100)
                self._ui(self._set_status, f"Done!{size_str}")
                self._ui(self._show_done_buttons, output_path)
            else:
                # Collect error
                err_text = b"".join(stderr_lines).decode('utf-8', errors='replace')
                # Get last useful line
                err_lines = [l.strip() for l in err_text.splitlines() if l.strip()]
                last_err = err_lines[-1] if err_lines else "Unknown error"
                if len(last_err) > 80:
                    last_err = last_err[:80] + "..."
                self._ui(self._set_status, f"Error: {last_err}")
                self._ui(self._enable_convert)

        except Exception as e:
            self._ui(self._set_status, f"Error: {e}")
            self._ui(self._enable_convert)

    def _enable_convert(self):
        try:
            self.convert_btn.config(state="normal", bg=self.GREEN)
        except:
            pass

    def _show_done_buttons(self, output_path):
        try:
            self.convert_btn.destroy()
            self.cancel_btn.master.destroy()

            bf = tk.Frame(self.root, bg=self.BG)
            bf.pack(pady=(0, 14))

            tk.Button(bf, text="Play Video", width=14,
                font=("Segoe UI", 10), fg=self.BG, bg=self.GREEN,
                activebackground="#94e2d5", relief="flat", cursor="hand2",
                command=lambda: os.startfile(output_path)
            ).pack(side="left", padx=6)

            tk.Button(bf, text="Open Folder", width=14,
                font=("Segoe UI", 10), fg=self.BG, bg=self.ACCENT,
                activebackground="#74c7ec", relief="flat", cursor="hand2",
                command=lambda: os.startfile(os.path.dirname(output_path))
            ).pack(side="left", padx=6)

            tk.Button(bf, text="Close", width=10,
                font=("Segoe UI", 10), fg=self.FG, bg=self.BTN_BG,
                activebackground="#585b70", relief="flat", cursor="hand2",
                command=self.root.destroy
            ).pack(side="left", padx=6)
        except:
            pass


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        root = tk.Tk()
        root.withdraw()
        choice = messagebox.askyesnocancel("Image Sequence to MP4",
            "Yes = Select an image file from a sequence\n"
            "No  = Select a folder containing a sequence\n"
            "Cancel = Exit")
        if choice is None:
            sys.exit(0)
        elif choice:
            path = filedialog.askopenfilename(title="Select Image from Sequence",
                filetypes=[
                    ("Image files", "*.png *.jpg *.jpeg *.exr *.tga *.tif *.tiff *.bmp *.dpx"),
                    ("All files", "*.*")])
        else:
            path = filedialog.askdirectory(title="Select Folder with Image Sequence")
        root.destroy()
        if not path:
            sys.exit(0)
    else:
        path = sys.argv[1]

    if os.path.isdir(path):
        seq = detect_sequence_in_directory(path)
        if not seq:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("No Sequence Found",
                f"No image sequence detected in:\n{path}")
            sys.exit(0)
        # Place the .mp4 next to the folder, not inside it
        parent_dir = os.path.dirname(os.path.normpath(path))
        ImagesToVideoGUI(seq, output_dir=parent_dir)

    elif os.path.isfile(path):
        seq = detect_sequence(path)
        if not seq:
            # Maybe it's a single image in a directory — try directory detection
            seq = detect_sequence_in_directory(os.path.dirname(path))
        if not seq:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("No Sequence Found",
                f"Could not detect an image sequence from:\n{os.path.basename(path)}\n\n"
                "Expected naming like: Name.0001.png")
            sys.exit(0)
        ImagesToVideoGUI(seq)

    else:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Path not found:\n{path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
