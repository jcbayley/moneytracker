@echo off
REM Build script for MoneyTracker Windows packaging

echo 💰 MoneyTracker Windows Build Script
echo ====================================

REM Check if virtual environment exists
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r ..\requirements.txt
pip install pyinstaller

REM Clean previous builds
echo [INFO] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "__pycache__" rmdir /s /q __pycache__

REM Build with PyInstaller
echo [INFO] Building executable with PyInstaller...
pyinstaller ..\packaging\MoneyTracker.spec --clean --noconfirm

REM Check if build was successful
if exist "dist\MoneyTracker.exe" (
    echo [SUCCESS] PyInstaller build completed successfully!
    echo [INFO] Executable created: dist\MoneyTracker.exe
    
    REM Rename for distribution
    move dist\MoneyTracker.exe dist\MoneyTracker-win64.exe
    
    echo.
    echo [INFO] Build information:
    dir dist\MoneyTracker-win64.exe
    echo.
    
    echo [SUCCESS] ✅ Build complete! You can now:
    echo   • Run directly: .\dist\MoneyTracker-win64.exe
    echo   • Distribute: MoneyTracker-win64.exe
    
) else (
    echo [ERROR] PyInstaller build failed!
    exit /b 1
)

REM Deactivate virtual environment
call venv\Scripts\deactivate.bat

echo.
echo [SUCCESS] 🎉 Windows build process completed!