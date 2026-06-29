@echo off
REM ============================================================
REM  LibriScribe GUI - Windows Installer Build Script
REM
REM  Prerequisites (must be on PATH):
REM    - Python 3.10+  with pip
REM    - Node.js 18+   with npm
REM    - Inno Setup 6  (iscc.exe on PATH, or set ISCC below)
REM ============================================================
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM -- Locate Inno Setup compiler --
where iscc >nul 2>&1
if %errorlevel%==0 (
    set "ISCC=iscc"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else (
    echo [ERROR] Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php
    echo         or add ISCC.exe to your PATH.
    exit /b 1
)

echo.
echo ============================================================
echo  Step 1/4: Install Python dependencies
echo ============================================================
pip install -e . || goto :error
pip install pyinstaller || goto :error

echo.
echo ============================================================
echo  Step 2/4: Build frontend
echo ============================================================
cd frontend
call npm install || goto :error
call npm run build || goto :error
cd ..

if not exist "frontend\dist\index.html" (
    echo [ERROR] Frontend build failed -- frontend/dist/index.html not found.
    exit /b 1
)

echo.
echo ============================================================
echo  Step 3/4: Bundle with PyInstaller
echo ============================================================
pyinstaller --noconfirm libriscribe.spec || goto :error

if not exist "dist\LibriScribeGUI\LibriScribeGUI.exe" (
    echo [ERROR] PyInstaller output not found.
    exit /b 1
)

echo.
echo ============================================================
echo  Step 4/4: Create Windows installer with Inno Setup
echo ============================================================
if not exist "installer\libriscribe.ico" (
    echo [WARNING] No icon file at installer\libriscribe.ico -- installer will use default icon.
)

if not exist "dist\installer" mkdir "dist\installer"
"%ISCC%" installer\libriscribe.iss || goto :error

echo.
echo ============================================================
echo  BUILD COMPLETE
echo ============================================================
echo  Installer: dist\installer\LibriScribeGUI-0.5.0-Setup.exe
echo ============================================================
exit /b 0

:error
echo.
echo [ERROR] Build failed at the step above.
exit /b 1
