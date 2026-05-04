@echo off
setlocal enabledelayedexpansion

echo =============================================
echo   Registro de tarea: Monex Excel Push
echo =============================================
echo.

rem Strip trailing backslash from script directory
set "SYNC_DIR=%~dp0"
if "!SYNC_DIR:~-1!"=="\" set "SYNC_DIR=!SYNC_DIR:~0,-1!"

set "XML_TEMPLATE=!SYNC_DIR!\excel_push_task.xml"
set "XML_READY=%TEMP%\excel_push_task_ready.xml"

echo Ruta detectada: !SYNC_DIR!
echo.

rem Replace placeholder with actual path and write to temp file
powershell -NoProfile -Command ^
  "(Get-Content '!XML_TEMPLATE!' -Encoding UTF8) -replace 'PLACEHOLDER_SYNC_DIR', '!SYNC_DIR!' | Set-Content '!XML_READY!' -Encoding Unicode"

if %ERRORLEVEL% NEQ 0 (
    echo Error al preparar el archivo de configuracion.
    pause
    exit /b 1
)

rem Import task into Task Scheduler (overwrites if already exists)
schtasks /create /xml "!XML_READY!" /tn "Monex Excel Push" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Tarea registrada correctamente.
    echo La sincronizacion iniciara automaticamente al iniciar sesion.
    echo.
    echo Para verificar: abrir "Programador de tareas" y buscar "Monex Excel Push".
    echo Para iniciar ahora sin reiniciar: schtasks /run /tn "Monex Excel Push"
) else (
    echo.
    echo Error al registrar la tarea.
    echo Asegurarse de ejecutar este archivo como Administrador.
    echo Clic derecho sobre registrar_tarea.bat ^> Ejecutar como administrador.
)

echo.
pause
