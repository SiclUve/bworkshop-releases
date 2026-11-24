@echo off
rem Construit l'exe puis l'installateur : dist\HarebourgOverlay-Setup.exe (necessite Inno Setup 6)
cd /d "%~dp0"
call build_exe.bat nopause || exit /b 1
set ISCC=
for %%p in ("%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe") do (
  if exist %%p set ISCC=%%~p
)
if not defined ISCC (
  echo Inno Setup 6 est introuvable. Installe-le : winget install JRSoftware.InnoSetup
  pause
  exit /b 1
)
"%ISCC%" installer.iss || (pause & exit /b 1)
echo.
echo Fini : dist\HarebourgOverlay-Setup.exe
pause
