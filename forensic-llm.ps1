# Forensic-LLM PowerShell Launcher Script
# This script allows you to run Forensic-LLM from anywhere by typing "forensic-llm"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Set-Location "Extractor"
python browse_scraper.py $args

