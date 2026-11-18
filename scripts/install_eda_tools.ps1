# PowerShell Toolchain Setup Script for RTL Optimizer AI Agent
# Installs Python packages and downloads OSS CAD Suite (Yosys + Icarus Verilog for Windows)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   RTL Optimizer AI Agent - Toolchain Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $ProjectRoot "tools"

if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir | Out-Null
}

# 1. Install Python requirements
Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
& python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

# 2. Check existing tools
$yosysFound = (Get-Command yosys.exe -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $ToolsDir "oss-cad-suite\bin\yosys.exe"))
$iverilogFound = (Get-Command iverilog.exe -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $ToolsDir "oss-cad-suite\bin\iverilog.exe"))

if ($yosysFound -and $iverilogFound) {
    Write-Host "`n[2/3] EDA tools (Yosys and Icarus Verilog) are already installed!" -ForegroundColor Green
} else {
    Write-Host "`n[2/3] Downloading OSS CAD Suite (Yosys, Icarus Verilog, VVP)..." -ForegroundColor Yellow
    
    # Download latest Windows OSS CAD Suite release
    $DownloadUrl = "https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2024-11-15/oss-cad-suite-windows-x64-20241115.exe"
    $DestExe = Join-Path $ToolsDir "oss-cad-suite-installer.exe"

    if (-not (Test-Path $DestExe)) {
        Write-Host "Fetching from: $DownloadUrl" -ForegroundColor Cyan
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $DestExe
    }

    Write-Host "Extracting OSS CAD Suite into $ToolsDir..." -ForegroundColor Yellow
    # Self extracting 7z archive
    Start-Process -FilePath $DestExe -ArgumentList "-o`"$ToolsDir`"", "-y" -Wait
    Write-Host "Extraction complete!" -ForegroundColor Green
}

# 3. Final Verification
Write-Host "`n[3/3] Verifying environment..." -ForegroundColor Yellow
& python (Join-Path $ProjectRoot "scripts\run_agent.py") check-tools

Write-Host "`nSetup successfully finished!" -ForegroundColor Green
