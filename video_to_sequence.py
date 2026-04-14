"""
Video to Image Sequence Converter - uses ffmpeg.
Right-click context menu integration for Windows 11.
Usage:
    python video_to_sequence.py "<path_to_video>"        (single file)
    python video_to_sequence.py "<path_to_directory>"    (batch - all videos in folder)
"""
import subprocess, sys, os, json, re, threading, glob
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

OUTPUT_FORMAT = "png"
JPEG_QUALITY = 2
PADDING = 4

VIDEO_EXTENSIONS = {".mp4",".mov",".avi",".mkv",".wmv",".flv",".webm",".m4v",".mpg",".mpeg",".ts",".mts",".m2ts"}

def get_video_info(path):
    cmd = ["ffprobe","-v","quiet","-print_format","json","-show_format","-show_streams",path]
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, startupinfo=si)
        if r.returncode == 0: return json.loads(r.stdout)
    except: pass
    return {}

def count_frames(info):
    for s in info.get("streams",[]):
        if s.get("codec_type")=="video":
            nb = s.get("nb_frames")
            if nb and nb!="N/A": return int(nb)
            dur = s.get("duration")
            rfr = s.get("r_frame_rate","0/1")
            if dur and dur!="N/A":
                try:
                    n,d = map(int, rfr.split("/"))
                    return int(float(dur)*(n/d if d else 0))
                except: pass
    fd = info.get("format",{}).get("duration")
    if fd:
        for s in info.get("streams",[]):
            if s.get("codec_type")=="video":
                try:
                    n,d = map(int, s.get("r_frame_rate","0/1").split("/"))
                    return int(float(fd)*(n/d if d else 0))
                except: pass
    return 0

def get_fps(info):
    for s in info.get("streams",[]):
        if s.get("codec_type")=="video":
            try:
                n,d = map(int, s.get("r_frame_rate","0/1").split("/"))
                return f"{n/d:.2f}" if d else "?"
            except: return "?"
    return "?"

def get_res(info):
    for s in info.get("streams",[]):
        if s.get("codec_type")=="video":
            return f"{s.get('width','?')}x{s.get('height','?')}"
    return "?"

def find_videos_in_dir(directory):
    """Find all video files in a directory (non-recursive)."""
    videos = []
    for f in sorted(os.listdir(directory)):
        ext = os.path.splitext(f)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            videos.append(os.path.join(directory, f))
    return videos

def is_already_converted(video_path, output_dir):
    """Check if a video has already been converted by comparing frame count."""
    if not os.path.isdir(output_dir):
        return False, 0
    existing = len([f for f in os.listdir(output_dir)
        if f.lower().endswith(f".{OUTPUT_FORMAT}")])
    if existing == 0:
        return False, 0
    # Get expected frame count from video
    info = get_video_info(video_path)
    expected = count_frames(info)
    # If we can't determine expected, check if folder has files at all
    if expected == 0:
        return (existing > 0), existing
    # Allow 2 frame tolerance (ffmpeg sometimes drops the last frame)
    if abs(existing - expected) <= 2:
        return True, existing
    return False, existing

def _count_output_files(output_dir):
    """Count output image files in the directory."""
    try:
        return len([f for f in os.listdir(output_dir)
            if f.lower().endswith(f".{OUTPUT_FORMAT}")])
    except FileNotFoundError:
        return 0

def convert_single(video_path, output_dir, on_progress=None, on_status=None, is_cancelled=None):
    """Convert a single video to image sequence. Returns (success, frame_count)."""
    import time
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    info = get_video_info(video_path)
    total_frames = count_frames(info)

    # Name.%04d.png  ->  Name.0001.png
    out_pattern = os.path.join(output_dir, f"{video_name}.%0{PADDING}d.{OUTPUT_FORMAT}")
    cmd = ["ffmpeg","-y","-i", video_path]
    if OUTPUT_FORMAT == "jpg":
        cmd += ["-qscale:v", str(JPEG_QUALITY)]
    cmd += [out_pattern]

    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, startupinfo=si)

    # Poll output directory for file count every second
    while proc.poll() is None:
        if is_cancelled and is_cancelled():
            proc.terminate()
            return False, 0
        current = _count_output_files(output_dir)
        if on_progress and total_frames > 0:
            on_progress(min(99.0, current / total_frames * 100))
        if on_status:
            txt = f"frame {current:,}"
            if total_frames: txt += f" / {total_frames:,}"
            on_status(txt)
        time.sleep(1.0)

    # Final count after ffmpeg exits
    actual = _count_output_files(output_dir)
    if on_progress:
        on_progress(100.0)
    if on_status:
        on_status(f"frame {actual:,}" + (f" / {total_frames:,}" if total_frames else ""))
    return (proc.returncode == 0), actual


class ConverterGUI:
    """GUI for single-file conversion."""
    def __init__(self, video_path):
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(video_path))[0]
        self.video_dir = os.path.dirname(video_path)
        self.output_dir = os.path.join(self.video_dir, f"{self.video_name}_frames")
        self.cancelled = False

        self.root = tk.Tk()
        self.root.title("Video to Image Sequence")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.root.attributes("-topmost", True)
        w, h = 520, 310
        sx = (self.root.winfo_screenwidth()-w)//2
        sy = (self.root.winfo_screenheight()-h)//2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Horizontal.TProgressbar", troughcolor="#313244",
            background="#89b4fa", darkcolor="#89b4fa", lightcolor="#89b4fa",
            bordercolor="#1e1e2e", thickness=18)

        px = {"padx": 20}
        tk.Label(self.root, text="Video to Image Sequence",
            font=("Segoe UI",14,"bold"), fg="#cdd6f4", bg="#1e1e2e").pack(pady=(18,4),**px,anchor="w")
        tk.Label(self.root, text=f"File:  {os.path.basename(video_path)}",
            font=("Segoe UI",10), fg="#a6adc8", bg="#1e1e2e").pack(pady=(0,2),**px,anchor="w")
        self.info_label = tk.Label(self.root, text="Analyzing video...",
            font=("Segoe UI",10), fg="#a6adc8", bg="#1e1e2e")
        self.info_label.pack(pady=(0,2),**px,anchor="w")
        self.out_label = tk.Label(self.root,
            text=f"Output:  ...\\{self.video_name}_frames\\",
            font=("Segoe UI",9), fg="#6c7086", bg="#1e1e2e")
        self.out_label.pack(pady=(0,12),**px,anchor="w")
        self.progress = ttk.Progressbar(self.root, length=470, mode="determinate",
            style="C.Horizontal.TProgressbar")
        self.progress.pack(pady=(0,6),**px)
        self.status_label = tk.Label(self.root, text="Preparing...",
            font=("Segoe UI",10), fg="#cdd6f4", bg="#1e1e2e")
        self.status_label.pack(pady=(0,14),**px,anchor="w")
        self.cancel_btn = tk.Button(self.root, text="Cancel", width=12,
            font=("Segoe UI",10), fg="#1e1e2e", bg="#f38ba8",
            activebackground="#eba0ac", relief="flat", cursor="hand2",
            command=self.cancel)
        self.cancel_btn.pack(pady=(0,14))
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        threading.Thread(target=self._run, daemon=True).start()
        self.root.mainloop()

    def cancel(self):
        self.cancelled = True
        self.root.destroy()

    def _ui(self, fn, *a):
        try: self.root.after(0, fn, *a)
        except: pass

    def _set_status(self, t): self.status_label.config(text=t)
    def _set_info(self, t): self.info_label.config(text=t)
    def _set_pct(self, v): self.progress["value"] = v

    def _run(self):
        try:
            info = get_video_info(self.video_path)
            fps = get_fps(info)
            res = get_res(info)
            total = count_frames(info)
            itxt = f"Resolution: {res}   |   FPS: {fps}"
            if total > 0: itxt += f"   |   ~{total:,} frames"
            self._ui(self._set_info, itxt)
            if self.cancelled: return

            self._ui(self._set_status, "Converting...  (frame 0)")

            def on_progress(pct):
                self._ui(self._set_pct, pct)
            def on_status(txt):
                self._ui(self._set_status, f"Converting...  {txt}")

            ok, actual = convert_single(
                self.video_path, self.output_dir,
                on_progress=on_progress,
                on_status=on_status,
                is_cancelled=lambda: self.cancelled)

            if self.cancelled: return
            self._ui(self._set_pct, 100)
            self._ui(self._set_status, f"Done! {actual:,} frames extracted")
            self._ui(self._done_buttons)
        except Exception as e:
            self._ui(self._set_status, f"Error: {e}")

    def _done_buttons(self):
        try:
            self.cancel_btn.destroy()
            bf = tk.Frame(self.root, bg="#1e1e2e")
            bf.pack(pady=(0,14))
            tk.Button(bf, text="Open Folder", width=14,
                font=("Segoe UI",10), fg="#1e1e2e", bg="#a6e3a1",
                activebackground="#94e2d5", relief="flat", cursor="hand2",
                command=lambda: os.startfile(self.output_dir)).pack(side="left",padx=6)
            tk.Button(bf, text="Close", width=10,
                font=("Segoe UI",10), fg="#cdd6f4", bg="#45475a",
                activebackground="#585b70", relief="flat", cursor="hand2",
                command=self.root.destroy).pack(side="left",padx=6)
        except: pass


class BatchConverterGUI:
    """GUI for batch directory conversion."""
    def __init__(self, directory):
        self.directory = directory
        self.videos = find_videos_in_dir(directory)
        self.cancelled = False

        if not self.videos:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Batch Convert", f"No video files found in:\n{directory}")
            sys.exit(0)

        self.root = tk.Tk()
        self.root.title("Batch Video to Image Sequence")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.root.attributes("-topmost", True)
        w, h = 560, 360
        sx = (self.root.winfo_screenwidth()-w)//2
        sy = (self.root.winfo_screenheight()-h)//2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Horizontal.TProgressbar", troughcolor="#313244",
            background="#89b4fa", darkcolor="#89b4fa", lightcolor="#89b4fa",
            bordercolor="#1e1e2e", thickness=18)
        style.configure("B.Horizontal.TProgressbar", troughcolor="#313244",
            background="#a6e3a1", darkcolor="#a6e3a1", lightcolor="#a6e3a1",
            bordercolor="#1e1e2e", thickness=12)

        px = {"padx": 20}
        tk.Label(self.root, text="Batch Video to Image Sequence",
            font=("Segoe UI",14,"bold"), fg="#cdd6f4", bg="#1e1e2e").pack(pady=(18,4),**px,anchor="w")
        tk.Label(self.root, text=f"Folder:  {os.path.basename(directory)}",
            font=("Segoe UI",10), fg="#a6adc8", bg="#1e1e2e").pack(pady=(0,2),**px,anchor="w")
        tk.Label(self.root, text=f"Found {len(self.videos)} video files",
            font=("Segoe UI",10), fg="#a6adc8", bg="#1e1e2e").pack(pady=(0,8),**px,anchor="w")

        # Overall progress
        tk.Label(self.root, text="Overall:",
            font=("Segoe UI",9), fg="#6c7086", bg="#1e1e2e").pack(pady=(0,2),**px,anchor="w")
        self.overall_progress = ttk.Progressbar(self.root, length=510, mode="determinate",
            style="B.Horizontal.TProgressbar")
        self.overall_progress.pack(pady=(0,8),**px)
        self.overall_label = tk.Label(self.root, text="0 / {0} files".format(len(self.videos)),
            font=("Segoe UI",10), fg="#cdd6f4", bg="#1e1e2e")
        self.overall_label.pack(pady=(0,10),**px,anchor="w")

        # Current file progress
        self.current_label = tk.Label(self.root, text="Waiting...",
            font=("Segoe UI",9), fg="#6c7086", bg="#1e1e2e")
        self.current_label.pack(pady=(0,2),**px,anchor="w")
        self.file_progress = ttk.Progressbar(self.root, length=510, mode="determinate",
            style="C.Horizontal.TProgressbar")
        self.file_progress.pack(pady=(0,4),**px)
        self.status_label = tk.Label(self.root, text="",
            font=("Segoe UI",10), fg="#cdd6f4", bg="#1e1e2e")
        self.status_label.pack(pady=(0,14),**px,anchor="w")

        self.cancel_btn = tk.Button(self.root, text="Cancel", width=12,
            font=("Segoe UI",10), fg="#1e1e2e", bg="#f38ba8",
            activebackground="#eba0ac", relief="flat", cursor="hand2",
            command=self.cancel)
        self.cancel_btn.pack(pady=(0,14))
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)
        threading.Thread(target=self._run, daemon=True).start()
        self.root.mainloop()

    def cancel(self):
        self.cancelled = True
        self.root.destroy()

    def _ui(self, fn, *a):
        try: self.root.after(0, fn, *a)
        except: pass

    def _run(self):
        total_files = len(self.videos)
        total_extracted = 0

        skipped = 0
        for i, vpath in enumerate(self.videos):
            if self.cancelled: return
            vname = os.path.splitext(os.path.basename(vpath))[0]
            out_dir = os.path.join(self.directory, f"{vname}_frames")

            self._ui(lambda t: self.current_label.config(text=t),
                f"File {i+1}/{total_files}:  {os.path.basename(vpath)}")
            self._ui(lambda: self.file_progress.__setitem__("value", 0))
            self._ui(lambda t: self.status_label.config(text=t), "Checking...")

            # Skip if already converted
            already_done, existing_count = is_already_converted(vpath, out_dir)
            if already_done:
                skipped += 1
                total_extracted += existing_count
                self._ui(lambda: self.file_progress.__setitem__("value", 100))
                self._ui(lambda t: self.status_label.config(text=t),
                    f"Skipped ({existing_count:,} frames already exist)")
                overall_pct = (i + 1) / total_files * 100
                overall_txt = f"{i+1} / {total_files} files  ({skipped} skipped, {total_extracted:,} total frames)"
                self._ui(lambda v=overall_pct: self.overall_progress.__setitem__("value", v))
                self._ui(lambda t=overall_txt: self.overall_label.config(text=t))
                continue

            def on_progress(pct):
                self._ui(lambda v=pct: self.file_progress.__setitem__("value", v))
            def on_status(txt):
                self._ui(lambda t=txt: self.status_label.config(text=f"Converting...  {t}"))

            ok, count = convert_single(vpath, out_dir,
                on_progress=on_progress,
                on_status=on_status,
                is_cancelled=lambda: self.cancelled)

            if self.cancelled: return
            total_extracted += count

            overall_pct = (i + 1) / total_files * 100
            overall_txt = f"{i+1} / {total_files} files  ({skipped} skipped, {total_extracted:,} total frames)"
            self._ui(lambda v=overall_pct: self.overall_progress.__setitem__("value", v))
            self._ui(lambda t=overall_txt: self.overall_label.config(text=t))

        self._ui(lambda: self.file_progress.__setitem__("value", 100))
        self._ui(lambda: self.status_label.config(
            text=f"Done! {total_files} videos -> {total_extracted:,} frames"))
        self._ui(self._done_buttons)

    def _done_buttons(self):
        try:
            self.cancel_btn.destroy()
            bf = tk.Frame(self.root, bg="#1e1e2e")
            bf.pack(pady=(0,14))
            tk.Button(bf, text="Open Folder", width=14,
                font=("Segoe UI",10), fg="#1e1e2e", bg="#a6e3a1",
                activebackground="#94e2d5", relief="flat", cursor="hand2",
                command=lambda: os.startfile(self.directory)).pack(side="left",padx=6)
            tk.Button(bf, text="Close", width=10,
                font=("Segoe UI",10), fg="#cdd6f4", bg="#45475a",
                activebackground="#585b70", relief="flat", cursor="hand2",
                command=self.root.destroy).pack(side="left",padx=6)
        except: pass


def main():
    if len(sys.argv) < 2:
        root = tk.Tk()
        root.withdraw()
        choice = messagebox.askyesnocancel("Video to Image Sequence",
            "Yes = Select a video file\nNo = Select a folder (batch)\nCancel = Exit")
        if choice is None:
            sys.exit(0)
        elif choice:
            path = filedialog.askopenfilename(title="Select Video File",
                filetypes=[("Video files","*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v *.mpg *.mpeg *.ts"),
                           ("All files","*.*")])
        else:
            path = filedialog.askdirectory(title="Select Folder with Videos")
        root.destroy()
        if not path: sys.exit(0)
    else:
        path = sys.argv[1]

    if os.path.isdir(path):
        BatchConverterGUI(path)
    elif os.path.isfile(path):
        ConverterGUI(path)
    else:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Path not found:\n{path}")
        sys.exit(1)

if __name__ == "__main__":
    main()
