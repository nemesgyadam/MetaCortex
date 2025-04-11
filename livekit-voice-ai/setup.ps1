# Setup script for LiveKit Voice AI
Write-Host "Setting up LiveKit Voice AI environment..." -ForegroundColor Green

# Activate the virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies using uv
Write-Host "Installing dependencies with uv..." -ForegroundColor Green
uv pip install -r requirements.txt

Write-Host "Setup complete!" -ForegroundColor Green