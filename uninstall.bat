@echo off
:: ═══════════════════════════════════════════════════════════════════════════
:: FFmpeg Sequence Tools - One-Click Uninstaller
:: Removes right-click context menu entries.
:: Must be run as Administrator!
:: ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   FFmpeg Sequence Tools - Uninstaller        ║
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

echo  [1/2] Removing "Convert to Image Sequence" ...
echo.
python "%~dp0install_context_menu.py" uninstall
echo.

echo  [2/2] Removing "Create MP4 from Image Sequence" ...
echo.
python "%~dp0install_images_to_video_menu.py" uninstall
echo.

echo  ╔══════════════════════════════════════════════╗
echo  ║   Uninstall Complete!                        ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
