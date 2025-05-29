@echo off
setlocal enabledelayedexpansion

REM --- GymManager Pro - Instalador Básico para Windows ---

echo =========================================================
echo   Instalador 
echo =========================================================
echo.

REM --- Paso 1: Verificar Python (muy básico) ---
echo Verificando instalacion de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no parece estar instalado o no esta en el PATH.
    echo Por favor, instale Python 3 (ej. desde python.org) y asegurese
    echo de marcar "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
) else (
    echo Python detectado.
)
echo.

REM --- Paso 2: (Opcional) Crear Entorno Virtual ---
set VENV_DIR=venv_gym_pro
echo Verificando/Creando entorno virtual en "%VENV_DIR%"...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creando entorno virtual...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual. Verifique su instalacion de Python.
        pause
        exit /b 1
    )
    echo Entorno virtual "%VENV_DIR%" creado.
) else (
    echo Entorno virtual "%VENV_DIR%" ya existe.
)
echo.

REM --- Paso 3: (Opcional) Activar Entorno Virtual e Instalar Dependencias ---
echo Activando entorno virtual (temporalmente para este script)...
call "%VENV_DIR%\Scripts\activate.bat"

REM Suponiendo que tenemos un archivo requirements.txt
REM Si no usas Pillow u otras librerías externas, puedes omitir esto o el requirements.txt
set REQUIREMENTS_FILE=requirements.txt
if exist "%REQUIREMENTS_FILE%" (
    echo Instalando dependencias desde %REQUIREMENTS_FILE%...
    pip install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo ADVERTENCIA: Hubo problemas al instalar algunas dependencias.
        echo La aplicacion podria no funcionar correctamente. Verifique los mensajes de error.
        echo Asegurese de tener pip actualizado (python -m pip install --upgrade pip).
        echo.
    ) else (
        echo Dependencias instaladas/verificadas.
    )
) else (
    echo ADVERTENCIA: Archivo %REQUIREMENTS_FILE% no encontrado.
    echo Si la aplicacion requiere bibliotecas externas (ej. Pillow para fotos),
    echo estas no seran instaladas y la aplicacion podria fallar.
    echo Puede crear un %REQUIREMENTS_FILE% con el contenido: Pillow
)
echo.

REM --- Paso 4: Preparar Directorios y Base de Datos ---
echo Preparando directorios de la aplicacion y base de datos...

REM Esta llamada ya se hace desde main_gui.py, pero ejecutarla aquí asegura todo
REM y es útil si el usuario no ejecuta main_gui.py inmediatamente.
REM Asumimos que los scripts de Python estan en el directorio actual o en subdirectorios
REM y que el archivo config.py es accesible.

REM cd core_logic REM Esto NO funcionaria si config.py esta en la raiz.
REM La logica de python debe manejar sus paths internos.

REM Llamamos a database.py directamente, que a su vez usa config.py y utils.py
REM para crear directorios y la BD.
REM La clave es que python pueda encontrar config.py desde core_logic/database.py
REM Si main_gui.py funciona, esta llamada también debería.
python "core_logic\database.py"
if %errorlevel% neq 0 (
    echo ERROR: Hubo un problema al inicializar la base de datos con 'core_logic\database.py'.
    echo Verifique los mensajes de error.
    pause
    exit /b 1
)
echo.

REM No es necesario llamar a initialize_superuser aquí, main_gui.py lo hará.

echo =========================================================
echo   Instalacion Basica Completada
echo =========================================================
echo.
echo PARA EJECUTAR LA APLICACION:
echo 1. (Si no lo esta ya) Active el entorno virtual:
echo    Abra una nueva ventana de comandos (cmd o PowerShell)
echo    Navegue a este directorio (%~dp0)
echo    Ejecute: "%VENV_DIR%\Scripts\activate.bat"
echo.
echo 2. Ejecute el script principal de la GUI:
echo    python main_gui.py
echo.
echo NOTA IMPORTANTE:
echo El superusuario por defecto es (ver config.py):
echo   Usuario: admin  (o el que hayas configurado en SUPERUSER_INIT_USERNAME)
echo   Contrasena: SecurePassword123! (o la que hayas configurado en SUPERUSER_INIT_PASSWORD)
echo   ¡¡SE RECOMIENDA CAMBIAR ESTA CONTRASENA INMEDIATAMENTE!!
echo.
echo =========================================================
echo.

REM Opcional: Desactivar el entorno virtual al final del script.
REM No es estrictamente necesario ya que el efecto de 'call' es para la sesión actual del script.
REM call "%VENV_DIR%\Scripts\deactivate.bat"

pause
exit /b 0