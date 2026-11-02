@echo off
if not exist ".venv\Scripts\python.exe" (
  echo First install dependencies by following README.md
  pause
  exit /b 1
)
".venv\Scripts\python.exe" screen_scroller.py
