@echo off
setlocal

set "ROOT=%~dp0"
pushd "%ROOT%"

if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3.12 -m venv .venv
    if errorlevel 1 py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 exit /b 1
)

echo Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

where npm >nul 2>nul
if errorlevel 1 (
  echo npm is required to build the frontend.
  exit /b 1
)

echo Building frontend...
pushd frontend
if exist package-lock.json (
  call npm ci
) else (
  call npm install
)
if errorlevel 1 (
  popd
  exit /b 1
)
call npm run build
if errorlevel 1 (
  popd
  exit /b 1
)
popd
if errorlevel 1 exit /b 1

echo Installing packaging dependency...
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 exit /b 1

echo Building portable backend bundle...
".venv\Scripts\python.exe" -m PyInstaller --clean --noconfirm pdf_matcher.spec
if errorlevel 1 exit /b 1

copy /Y "run.bat" "dist\pdf_matcher\run.bat" >nul

echo Build completed.
echo Portable output folder: dist\pdf_matcher
popd
