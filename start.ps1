# DRC-ATEN Application Launcher
$Host.UI.RawUI.WindowTitle = "DRC-ATEN Production Server"

# Change to script directory
Set-Location $PSScriptRoot

# Activate virtual environment
& "venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "========================================"
Write-Host "   DRC-ATEN Production Server"
Write-Host "========================================"
Write-Host ""
Write-Host "Starting application with PyWebView..."
Write-Host "Close the window to stop the server"
Write-Host ""

# Run PyWebView launcher
python start_webview.py

# When window closes
Write-Host ""
Write-Host "Application stopped."
Start-Sleep -Seconds 2
