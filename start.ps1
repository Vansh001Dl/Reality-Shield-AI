#!/usr/bin/env pwsh
# RealityShield-AI: Project Startup Script
# This script starts both backend and frontend services in separate PowerShell windows

param(
    [Parameter(ParameterSetName = 'Dev')]
    [switch]$Dev,

    [Parameter(ParameterSetName = 'Prod')]
    [switch]$Prod,

    [Parameter(ParameterSetName = 'Docker')]
    [switch]$Docker,

    [Parameter(ParameterSetName = 'Check')]
    [switch]$Check,

    [Parameter(ParameterSetName = 'Install')]
    [switch]$Install
)

$ErrorActionPreference = 'Stop'

# Get project paths
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'

# Find Python virtual environment
$pythonPath = Join-Path $backendDir '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonPath)) {
    $pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
}

if (-not (Test-Path $pythonPath)) {
    Write-Warning "Python virtual environment not found. Creating one..."
    & python -m venv "$backendDir\.venv"
    $pythonPath = Join-Path $backendDir '.venv\Scripts\python.exe'
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Cyan

    # Check Node.js
    try {
        $nodeVersion = node --version
        Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
    } catch {
        Write-Warning "Node.js not found. Please install Node.js 18+."
    }

    # Check Python
    try {
        $pythonVersion = & $pythonPath --version
        Write-Host "  Python: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Warning "Python not found."
    }

    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Host "  Docker: $dockerVersion" -ForegroundColor Green
    } catch {
        Write-Warning "Docker not found. Docker is required for full functionality."
    }

    # Check PostgreSQL
    try {
        $pgVersion = psql --version
        Write-Host "  PostgreSQL: $pgVersion" -ForegroundColor Green
    } catch {
        Write-Warning "PostgreSQL CLI not found."
    }

    Write-Host "Prerequisites check complete." -ForegroundColor Cyan
}

# Function to install dependencies
function Install-Dependencies {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan

    # Install Python dependencies
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    & $pythonPath -m pip install --upgrade pip
    & $pythonPath -m pip install -r "$backendDir\requirements.txt"
    Write-Host "  Python dependencies installed." -ForegroundColor Green

    # Install Node.js dependencies
    Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
    Set-Location $frontendDir
    & npm install
    Set-Location $repoRoot
    Write-Host "  Node.js dependencies installed." -ForegroundColor Green

    Write-Host "All dependencies installed." -ForegroundColor Cyan
}

# Function to start development servers
function Start-DevServers {
    Write-Host "Starting RealityShield-AI in DEVELOPMENT mode..." -ForegroundColor Green

    $devDatabasePath = (Join-Path $backendDir 'data\users.sqlite3').Replace('\', '/')
    $devDatabaseUrl = "sqlite:///$devDatabasePath"

    # Check for .env file
    $envFile = Join-Path $repoRoot '.env'
    if (-not (Test-Path $envFile)) {
        Write-Warning ".env file not found. Creating from .env.example..."
        Copy-Item (Join-Path $repoRoot '.env.example') $envFile
        Write-Host "  Please edit .env file and add your API keys." -ForegroundColor Yellow
    }

    # Start backend
    Start-Process powershell.exe -WorkingDirectory $backendDir -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-Command', "`$env:APP_ENV = 'development'; `$env:DATABASE_URL = '$devDatabaseUrl'; `$host.UI.RawUI.WindowTitle = 'RealityShield Backend'; & '$pythonPath' -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
    )

    # Start frontend
    Start-Process powershell.exe -WorkingDirectory $frontendDir -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-Command', "`$host.UI.RawUI.WindowTitle = 'RealityShield Frontend'; & npm run dev -- --host 0.0.0.0 --port 5173"
    )

    # Wait for services to start
    Start-Sleep -Seconds 3

    Write-Host "RealityShield-AI services started." -ForegroundColor Green
    Write-Host "  Backend API:  http://127.0.0.1:8001" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://127.0.0.1:5173" -ForegroundColor Cyan
    Write-Host "  API Docs:    http://127.0.0.1:8001/api/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To stop services, close the PowerShell windows." -ForegroundColor Yellow
}

# Function to start Docker services
function Start-Docker {
    Write-Host "Starting RealityShield-AI with Docker..." -ForegroundColor Green

    Set-Location $repoRoot
    docker-compose up --build

    Write-Host "RealityShield-AI Docker services started." -ForegroundColor Green
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  Backend:  http://localhost:8001" -ForegroundColor Cyan
    Write-Host "  API Docs: http://localhost:8001/docs" -ForegroundColor Cyan
}

# Main script logic
if ($Check) {
    Test-Prerequisites
    exit
}

if ($Install) {
    Install-Dependencies
    exit
}

if ($Prod) {
    Write-Host "Production mode not yet configured. Use -Docker for production." -ForegroundColor Yellow
    exit
}

if ($Docker) {
    Start-Docker
    exit
}

# Default: Development mode
Test-Prerequisites
Start-DevServers
