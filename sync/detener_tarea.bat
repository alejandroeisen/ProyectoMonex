@echo off
echo =============================================
echo   Detener y eliminar: Monex Excel Push
echo =============================================
echo.

schtasks /End /TN "Monex Excel Push" >nul 2>&1
taskkill /IM pythonw.exe /F >nul 2>&1

schtasks /Delete /TN "Monex Excel Push" /F >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Tarea eliminada correctamente.
    echo La sincronizacion no volvera a iniciarse automaticamente.
) else (
    echo La tarea no existia o ya habia sido eliminada.
)

echo.
pause
