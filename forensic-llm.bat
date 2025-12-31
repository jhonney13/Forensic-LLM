@echo off
REM Forensic-LLM Launcher Script
REM This script allows you to run Forensic-LLM from anywhere by typing "forensic-llm"

cd /d "%~dp0"
cd Extractor
python browse_scraper.py %*

