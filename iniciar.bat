@echo off
rem Levanta Verdad Contable en local: backend (puerto 8000), frontend (puerto 5173) y abre el navegador.
rem Cada servidor queda en su propia ventana; para apagarlo, cierra esa ventana o pulsa Ctrl+C en ella.
setlocal
cd /d "%~dp0"

rem Backend: si el puerto 8000 ya esta ocupado, se asume que ya esta corriendo.
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if errorlevel 1 (
    start "Verdad Contable - backend" /d "%~dp0backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --port 8000"
) else (
    echo Backend ya esta corriendo en el puerto 8000.
)

rem Frontend: igual con el puerto 5173.
netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul
if errorlevel 1 (
    start "Verdad Contable - frontend" /d "%~dp0frontend" cmd /k "npm run dev"
) else (
    echo Frontend ya esta corriendo en el puerto 5173.
)

rem Esperar a que Vite arranque antes de abrir el navegador.
timeout /t 5 /nobreak >nul
start "" http://localhost:5173
endlocal
