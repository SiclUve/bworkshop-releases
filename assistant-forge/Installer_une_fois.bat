@echo off
cd /d "%~dp0"
echo Installation des composants (une seule fois, internet necessaire)...
py -3.13 -m pip install -r requirements.txt
echo.
echo Termine. Tu peux fermer cette fenetre et lancer Lancer_assistant.bat.
pause
