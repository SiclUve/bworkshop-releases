@echo off
rem Construit HarebourgOverlay.exe (un seul fichier, sans Python a installer) dans le dossier dist\
cd /d "%~dp0"
py -3 -m pip install -q -r requirements.txt pyinstaller pillow || goto :err
if not exist icon.ico py -3 make_icon.py
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name HarebourgOverlay --icon icon.ico --version-file version_info.txt ^
  --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 ^
  --exclude-module PIL --exclude-module cv2 --exclude-module tkinter --exclude-module scipy --exclude-module matplotlib ^
  overlay.py || goto :err
rmdir /s /q build 2>nul
del /q HarebourgOverlay.spec 2>nul
echo.
echo Fini : dist\HarebourgOverlay.exe
if /i not "%1"=="nopause" pause
exit /b 0
:err
echo La construction a echoue, envoie-moi le message ci-dessus.
if /i not "%1"=="nopause" pause
exit /b 1
