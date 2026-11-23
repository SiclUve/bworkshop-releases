@echo off
cd /d "%~dp0"
title Assistant forgemagie
echo Assistant forgemagie : observation seule, aucune action dans le jeu.
py -3.13 -c "import mss, cv2, numpy, rapidocr_onnxruntime, PIL" 2>nul
if errorlevel 1 (
  echo Il manque des composants. Double-clique d'abord sur Installer_une_fois.bat
  pause
  exit /b 1
)
py -3.13 fenetre_forge.py
if errorlevel 1 (
  echo.
  echo Le programme s'est arrete avec une erreur. Copie le message ci-dessus et envoie-le moi.
  pause
)
