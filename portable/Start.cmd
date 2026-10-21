@echo off
setlocal
chcp 65001 >nul
"%~dp0PocketAgent.exe" %*
set "pocket_exit=%ERRORLEVEL%"
if not "%pocket_exit%"=="0" pause
exit /b %pocket_exit%

