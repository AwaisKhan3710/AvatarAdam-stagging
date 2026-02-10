# AvatarAdam Server Startup Script
# This script starts the backend server with proper environment setup

Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         AvatarAdam Backend Server Startup                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get the project root directory
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Write-Host "Project Root: $projectRoot" -ForegroundColor Yellow
Write-Host "Backend Dir: $backendDir" -ForegroundColor Yellow
Write-Host "Python: $venvPython" -ForegroundColor Yellow
Write-Host ""

# Check if .env file exists
$envFile = Join-Path $backendDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "⚠️  .env file not found at $envFile" -ForegroundColor Yellow
    Write-Host "Creating minimal .env file for development..." -ForegroundColor Yellow
    
    $envContent = @"
# Application
PROJECT_NAME=Avatar Adam
VERSION=0.1.0
DEBUG=true

# Database - Using SQLite for development (no PostgreSQL required)
DATABASE_URL=sqlite:///./avatar_adam.db

# Security - Generate with: openssl rand -hex 32
SECRET_KEY=dev-secret-key-change-in-production-12345678901234567890

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]

# Optional - Add your API keys here
OPENROUTER_API_KEY=
ELEVENLABS_API_KEY=
OPENAI_API_KEY=
PINECONE_API_KEY=
HEYGEN_API_KEY=
"@
    
    Set-Content -Path $envFile -Value $envContent
    Write-Host "✓ Created .env file" -ForegroundColor Green
    Write-Host ""
}

# Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Cyan
$env:PROJECT_NAME = "Avatar Adam"
$env:VERSION = "0.1.0"
$env:DEBUG = "true"
$env:DATABASE_URL = "sqlite:///./avatar_adam.db"
$env:SECRET_KEY = "dev-secret-key-change-in-production-12345678901234567890"
$env:BACKEND_CORS_ORIGINS = '["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]'

Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host ""

# Start the server
Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "Server will be available at: http://127.0.0.1:8001" -ForegroundColor Green
Write-Host "Swagger UI: http://127.0.0.1:8001/docs" -ForegroundColor Green
Write-Host "ReDoc: http://127.0.0.1:8001/redoc" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Change to backend directory and start server
Set-Location $backendDir
& $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
