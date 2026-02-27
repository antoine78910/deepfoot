@echo off
REM Lance l'ingestion des matchs avec le venv activé
REM En PowerShell : .\run_ingest.bat  (obligatoire)
cd /d "%~dp0"
call venv\Scripts\activate.bat
python scripts/ingest_matches.py
pause
