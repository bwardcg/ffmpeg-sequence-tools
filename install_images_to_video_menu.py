"""
Install / Uninstall right-click context menu entry for Image Sequence to MP4.
Must be run as Administrator.

Usage:
    python install_images_to_video_menu.py install
    python install_images_to_video_menu.py uninstall
"""
import sys
import os
import winreg
import ctypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERTER_SCRIPT = os.path.join(SCRIPT_DIR, "images_to_video.py")

MENU_NAME = "Create MP4 from Image Sequence"
DIR_MENU_NAME = "Create MP4 from Image Sequence"
REG_KEY_NAME = "ImageSequenceToMP4"

IMAGE_EXTENSIONS = [
    ".png", ".jpg", ".jpeg", ".exr", ".tga",
    ".tif", ".tiff", ".bmp", ".dpx",
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_python_path():
    return sys.executable

def install():
    python = get_python_path()
    command = f'"{python}" "{CONVERTER_SCRIPT}" "%1"'

    for ext in IMAGE_EXTENSIONS:
        key_path = f"SystemFileAssociations\\{ext}\\shell\\{REG_KEY_NAME}"
        try:
            key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_NAME)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "imageres.dll,-70")
            winreg.CloseKey(key)

            cmd_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + "\\command")
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
            winreg.CloseKey(cmd_key)

            print(f"  Registered: {ext}")
        except PermissionError:
            print(f"  FAILED (access denied): {ext}")
        except Exception as e:
            print(f"  FAILED: {ext} -> {e}")

    # Also register folder context menu
    folder_key_path = f"Directory\\shell\\{REG_KEY_NAME}"
    try:
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, folder_key_path)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, DIR_MENU_NAME)
        winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "imageres.dll,-70")
        winreg.CloseKey(key)
        cmd_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, folder_key_path + "\\command")
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
        winreg.CloseKey(cmd_key)
        print(f"  Registered: Folder")
    except Exception as e:
        print(f"  FAILED: Folder -> {e}")

    print(f"\nDone! Context menu entries installed.")
    print("Note: On Windows 11, right-click -> 'Show more options' to see classic menu entries.")

def uninstall():
    for ext in IMAGE_EXTENSIONS:
        key_path = f"SystemFileAssociations\\{ext}\\shell\\{REG_KEY_NAME}"
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + "\\command")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
            print(f"  Removed: {ext}")
        except FileNotFoundError:
            print(f"  Not found (already removed): {ext}")
        except Exception as e:
            print(f"  FAILED: {ext} -> {e}")

    folder_key_path = f"Directory\\shell\\{REG_KEY_NAME}"
    try:
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, folder_key_path + "\\command")
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, folder_key_path)
        print(f"  Removed: Folder")
    except FileNotFoundError:
        print(f"  Not found: Folder")
    except Exception as e:
        print(f"  FAILED: Folder -> {e}")

    print(f"\nDone! Context menu entries removed.")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "uninstall"):
        print("Usage:")
        print("  python install_images_to_video_menu.py install")
        print("  python install_images_to_video_menu.py uninstall")
        sys.exit(1)

    action = sys.argv[1]

    if not is_admin():
        print("Relaunching as Administrator...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{os.path.abspath(__file__)}" {action}', None, 1
        )
        sys.exit(0)

    print(f"{'Installing' if action == 'install' else 'Uninstalling'} context menu entries...\n")

    if action == "install":
        if not os.path.isfile(CONVERTER_SCRIPT):
            print(f"ERROR: Converter script not found at:\n  {CONVERTER_SCRIPT}")
            sys.exit(1)
        install()
    else:
        uninstall()

    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
