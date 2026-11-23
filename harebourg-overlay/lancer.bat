@echo off
cd /d "%~dp0"
set PY=
py -3 -c "import sys" >nul 2>&1 && set PY=py -3
if not defined PY (
  python -c "import sys" >nul 2>&1 && set PY=python
)
if not defined PY (
  echo Il faut Python 3 : winget install Python.Python.3.12
  echo puis relance ce fichier.
  pause
  exit /b 1
)
echo Installation des dependances (rapide, seulement PyQt6 et pynput)...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo L'installation a echoue. Envoie-moi le message d'erreur ci-dessus.
  pause
  exit /b 1
)
%PY% overlay.py
pause
