@echo off
py -m uvicorn girp.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
