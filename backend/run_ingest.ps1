# Lance l'ingestion des matchs avec le venv activé
# Usage (PowerShell) : .\run_ingest.ps1
Set-Location $PSScriptRoot
& .\venv\Scripts\python.exe scripts/ingest_matches.py
