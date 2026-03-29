@echo off
setlocal EnableExtensions

set "RAVEBERRY_ENV=Raveberry"
set "RAVEBERRY_CONFIG=%USERPROFILE%\raveberry.yaml"

set "CONDA_BAT="

if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "%USERPROFILE%\miniforge3\condabin\conda.bat" set "CONDA_BAT=%USERPROFILE%\miniforge3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\miniconda3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\miniconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\anaconda3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\anaconda3\condabin\conda.bat"
if not defined CONDA_BAT if exist "C:\ProgramData\miniforge3\condabin\conda.bat" set "CONDA_BAT=C:\ProgramData\miniforge3\condabin\conda.bat"

if not defined CONDA_BAT (
    echo.
    echo [ERROR] Could not find conda.bat.
    echo Edit this file and set CONDA_BAT manually if your Conda install is elsewhere.
    pause
    exit /b 1
)

call "%CONDA_BAT%" activate "%RAVEBERRY_ENV%"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate Conda environment "%RAVEBERRY_ENV%".
    echo If you used a different env name in the installer, change RAVEBERRY_ENV in this file.
    pause
    exit /b 1
)

if not defined CONDA_PREFIX (
    echo.
    echo [ERROR] CONDA_PREFIX is missing after activation.
    pause
    exit /b 1
)

set "DJANGO_USE_SQLITE=0"
set "POSTGRES_HOST=127.0.0.1"
set "POSTGRES_PORT=54329"
set "POSTGRES_DB=raveberry"
set "POSTGRES_USER=raveberry"
set "POSTGRES_PASSWORD=raveberry"
set "PGPASSWORD=%POSTGRES_PASSWORD%"

if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "RAVEBERRY_PGROOT=%LOCALAPPDATA%\Raveberry\postgres"
set "RAVEBERRY_PGDATA=%RAVEBERRY_PGROOT%\data"
set "RAVEBERRY_PGLOG=%RAVEBERRY_PGROOT%\postgres.log"

set "PATH=%CONDA_PREFIX%\Library\bin;%PATH%"

call :ensure_local_postgres
if errorlevel 1 (
    echo.
    echo [ERROR] PostgreSQL bootstrap failed.
    pause
    exit /b 1
)

set "RAVEBERRY_SCRIPT=%CONDA_PREFIX%\Scripts\raveberry"

if not exist "%RAVEBERRY_SCRIPT%" (
    echo.
    echo [ERROR] Raveberry launcher not found:
    echo %RAVEBERRY_SCRIPT%
    pause
    exit /b 1
)

set "RB_QUEUE_COUNT=0"
set "RB_CURRENT_COUNT=0"

for /f "usebackq tokens=1,2" %%A in (`python -c "import os, sys, pathlib, raveberry; base=pathlib.Path(raveberry.__file__).resolve().parent; os.chdir(base); sys.path.insert(0, str(base)); os.environ['DJANGO_SETTINGS_MODULE']='main.settings'; os.environ['DJANGO_DEBUG']='1'; import django; django.setup(); from core.models import QueuedSong, CurrentSong; print(f'{QueuedSong.objects.count()} {CurrentSong.objects.count()}')"` ) do (
    set "RB_QUEUE_COUNT=%%A"
    set "RB_CURRENT_COUNT=%%B"
)

echo.
if "%RB_QUEUE_COUNT%"=="0" if "%RB_CURRENT_COUNT%"=="0" (
    echo No saved queue or current song was found from the last session.
) else (
    echo Found saved playback state from the last session:
    echo   Queued songs: %RB_QUEUE_COUNT%
    echo   Current song entry: %RB_CURRENT_COUNT%
    echo.
    choice /C YN /N /M "Reset the saved queue/current song before starting? [Y/N]: "
    echo.
    if errorlevel 2 (
        echo Keeping saved queue/current song and resuming previous session state if available.
    ) else (
        python -c "import os, sys, pathlib, raveberry; base=pathlib.Path(raveberry.__file__).resolve().parent; os.chdir(base); sys.path.insert(0, str(base)); os.environ['DJANGO_SETTINGS_MODULE']='main.settings'; os.environ['DJANGO_DEBUG']='1'; import django; django.setup(); from core.models import QueuedSong, CurrentSong; QueuedSong.objects.all().delete(); CurrentSong.objects.all().delete()"
        if errorlevel 1 (
            echo [WARNING] Failed to clear the saved queue/current song. Starting anyway.
        ) else (
            echo Saved queue/current song was cleared.
        )
    )
)

title Raveberry
echo.
echo Starting Raveberry...
echo Env:    %RAVEBERRY_ENV%
echo Config: %RAVEBERRY_CONFIG%
echo URL:    http://127.0.0.1:8080/
echo.

python "%RAVEBERRY_SCRIPT%" run --nomopidy
set "RB_EXIT=%ERRORLEVEL%"

echo.
if not "%RB_EXIT%"=="0" (
    echo Raveberry exited with code %RB_EXIT%.
) else (
    echo Raveberry stopped.
)
pause
exit /b %RB_EXIT%

:ensure_local_postgres
where initdb >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Installing PostgreSQL server/client into the active Conda environment...
    call conda install -y -c conda-forge postgresql psycopg2
    if errorlevel 1 exit /b 1
    set "PATH=%CONDA_PREFIX%\Library\bin;%PATH%"
)

python -c "import psycopg2" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Installing psycopg2 into the active Conda environment...
    call conda install -y -c conda-forge psycopg2
    if errorlevel 1 exit /b 1
)

if not exist "%RAVEBERRY_PGROOT%" mkdir "%RAVEBERRY_PGROOT%"
if errorlevel 1 exit /b 1

if not exist "%RAVEBERRY_PGDATA%\PG_VERSION" (
    echo.
    echo [INFO] Initializing local PostgreSQL data directory...
    initdb -D "%RAVEBERRY_PGDATA%" -U postgres -A trust
    if errorlevel 1 exit /b 1

    >> "%RAVEBERRY_PGDATA%\postgresql.conf" echo listen_addresses = '127.0.0.1'
    >> "%RAVEBERRY_PGDATA%\postgresql.conf" echo port = %POSTGRES_PORT%
)

pg_isready -h %POSTGRES_HOST% -p %POSTGRES_PORT% -d postgres >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Starting local PostgreSQL...
    pg_ctl -D "%RAVEBERRY_PGDATA%" -l "%RAVEBERRY_PGLOG%" -o "-p %POSTGRES_PORT%" -w start
    if errorlevel 1 exit /b 1
)

timeout /t 2 /nobreak >nul

pg_isready -h %POSTGRES_HOST% -p %POSTGRES_PORT% -d postgres >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Local PostgreSQL is still not accepting connections after startup.
    exit /b 1
)

psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U postgres -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='%POSTGRES_USER%'" 2>nul | findstr /R "^[ ]*1[ ]*$" >nul
if errorlevel 1 (
    echo.
    echo [INFO] Creating PostgreSQL role %POSTGRES_USER%...
    psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U postgres -d postgres -c "CREATE ROLE %POSTGRES_USER% LOGIN PASSWORD '%POSTGRES_PASSWORD%';"
    if errorlevel 1 exit /b 1
)

psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='%POSTGRES_DB%'" 2>nul | findstr /R "^[ ]*1[ ]*$" >nul
if errorlevel 1 (
    echo.
    echo [INFO] Creating PostgreSQL database %POSTGRES_DB%...
    createdb -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U postgres -O %POSTGRES_USER% %POSTGRES_DB%
    if errorlevel 1 exit /b 1
)

exit /b 0
