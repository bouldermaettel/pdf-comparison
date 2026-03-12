@echo off
setlocal EnableExtensions

set "HOST=127.0.0.1"
set "PORT=8000"
set "URL=http://%HOST%:%PORT%/"
set "APP_EXE=%~dp0pdf_matcher.exe"

if not exist "%APP_EXE%" (
	echo Could not find %APP_EXE%
	echo Run this script from the same folder as pdf_matcher.exe.
	echo If you extracted a zip, ensure you extracted the full folder structure.
	pause
	exit /b 1
)

echo Starting backend...
start "PDF Matcher" "%APP_EXE%"

for /L %%I in (1,1,30) do (
	powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%URL%api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
	if not errorlevel 1 goto :ready
	timeout /t 1 /nobreak >nul
)

echo Backend did not become ready on %URL% within 30 seconds.
echo Try running pdf_matcher.exe directly to see error details.
echo Common cause: Windows blocked execution or missing runtime components.
pause
exit /b 1

:ready
echo Backend is ready. Opening browser...
start "" "%URL%"
exit /b 0
