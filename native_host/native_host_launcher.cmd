@echo off
set "ROOT=%~dp0.."
cd /d "%ROOT%"
set "PYTHONPATH=%ROOT%"
".venv\Scripts\python.exe" "%ROOT%\native_host\native_host.py"
