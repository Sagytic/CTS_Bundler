@echo off
REM Run from repo root: scripts\capture-test-results.bat
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0capture-test-results.ps1"
exit /b %ERRORLEVEL%
