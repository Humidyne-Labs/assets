@echo off
setlocal

:: Set source path (defaults to .agents located next to this script)
set "SOURCE=%~dp0.agents"

if not exist "%SOURCE%" (
    echo [ERROR] Source folder not found: "%SOURCE%"
    echo Place this script in the parent folder of .agents or update the SOURCE path.
    pause
    exit /b 1
)

:: Define target directories
for %%D in (
    "C:\Users\Matt\Documents\GitHub\esp32-s3_bsp"
    "C:\Users\Matt\Documents\GitHub\humid1-os\Source_Code\humid1_os_cpp"
) do (
    echo.
    echo ========================================================
    echo Target: %%~D
    echo ========================================================

    if exist "%%~D\.agents" (
        echo Removing existing .agents directory...
        rmdir /s /q "%%~D\.agents"
    )

    echo Copying fresh .agents directory...
    robocopy "%SOURCE%" "%%~D\.agents" /E /R:1 /W:1 >nul

    if errorlevel 8 (
        echo [FAIL] Error copying files to %%~D\.agents
    ) else (
        echo [OK] Successfully copied to %%~D\.agents
    )
)

echo.
echo All targets processed.
pause