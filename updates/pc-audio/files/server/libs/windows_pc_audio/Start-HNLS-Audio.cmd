@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Send-HNLS-Audio.ps1"
echo.
pause
