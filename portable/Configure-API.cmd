@echo off
setlocal
chcp 65001 >nul
"%~dp0PocketAgent.exe" --configure
if errorlevel 1 pause

