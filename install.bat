@echo off
:: ═══════════════════════════════════════════════════════════════════════════
:: FFmpeg Sequence Tools - One-Click Installer
:: Installs right-click context menu entries for:
::   1. Video to Image Sequence
::   2. Image Sequence to MP4
:: Must be run as Administrator!
:: ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   FFmpeg Sequence Tools - Installer          ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Administrator privileges required.
    echo      Right-click this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python not found. Please install Python 3.10+ first.
    echo      https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Check for FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] FFmpeg not found on PATH. Please install FFmpeg first.
    echo      https://www.gyan.dev/ffmpeg/builds/
    echo.
    pause
    exit /b 1
)

echo  [1/2] Installing "Convert to Image Sequence" ...
echo.
python "%~dp0install_context_menu.py" install
echo.

echo  [2/2] Installing "Create MP4 from Image Sequence" ...
echo.
python "%~dp0install_images_to_video_menu.py" install
echo.

echo  ╔══════════════════════════════════════════════╗
echo  ║   Installation Complete!                     ║
echo  ╚══════════════════════════════════════════════╝
echo.
echo  Right-click video files or image files to use.
echo  On Windows 11, click "Show more options" first.
echo.
pause
