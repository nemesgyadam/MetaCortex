@echo off
echo Setting up LiveKit Voice AI environment...

REM Create virtual environment using uv
uv venv .venv

REM Install dependencies
.\.venv\Scripts\uv pip install -r requirements.txt

echo Setup complete!
echo To activate the environment, run: .\.venv\Scripts\activate.bat