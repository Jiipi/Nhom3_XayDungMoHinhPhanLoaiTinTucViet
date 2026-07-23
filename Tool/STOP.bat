@echo off
setlocal EnableDelayedExpansion
REM ========================================
REM  DUNG CAO BAO - STOP CRAWLER
REM ========================================
REM
REM  Chay file nay de dung tat ca nguon bao
REM  dang cao. Du lieu da cao se duoc tu dong
REM  luu vao Tool/data/ (CSV + JSON).
REM  Chay lai START.bat de tiep tuc (resume).
REM ========================================

echo.
echo ========================================
echo   DUNG CAO BAO (STOP CRAWLER)
echo ========================================
echo.

cd /d "%~dp0"

set "PS_CMD=powershell"
set "GRACE_SECONDS=20"
set "MATCH_EXPR=main\.py|run\.py|crawl_all\.py|crawl_large_scale\.py"

where powershell >nul 2>&1
if errorlevel 1 (
	where pwsh >nul 2>&1
	if errorlevel 1 (
		set "PS_CMD="
	) else (
		set "PS_CMD=pwsh"
	)
)

REM Tao file STOP.flag de bao hieu cho crawler dung
echo STOP > "%~dp0STOP.flag"

echo [OK] Da gui tin hieu DUNG (STOP.flag).

if not defined PS_CMD (
	echo [!] Khong tim thay PowerShell. STOP.flag da duoc tao.
	echo [!] Neu crawler van chay, hay dong cua so dang chay tool sau vai giay.
	echo.
	pause
	exit /b 0
)

set "RUNNING_COUNT=0"
for /f %%I in ('%PS_CMD% -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match '%MATCH_EXPR%') }; (@($procs)).Count"') do set "RUNNING_COUNT=%%I"

if not defined RUNNING_COUNT set "RUNNING_COUNT=0"

if "%RUNNING_COUNT%"=="0" (
	echo [*] Khong tim thay tien trinh crawler nao dang chay.
	echo [*] STOP.flag se duoc crawler doc neu ban vua khoi dong lai trong cua so khac.
	echo.
	pause
	exit /b 0
)

echo [*] Tim thay %RUNNING_COUNT% tien trinh crawler dang chay.
echo [*] Dang cho toi da %GRACE_SECONDS%s de crawler tu luu checkpoint va tu thoat...

for /l %%S in (1,2,%GRACE_SECONDS%) do (
	timeout /t 2 >nul
	set "RUNNING_COUNT=0"
	for /f %%I in ('%PS_CMD% -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match '%MATCH_EXPR%') }; (@($procs)).Count"') do set "RUNNING_COUNT=%%I"
	if not defined RUNNING_COUNT set "RUNNING_COUNT=0"
	if "!RUNNING_COUNT!"=="0" goto :stopped_gracefully
)

REM Neu qua thoi gian grace ma van chua thoat, force stop cac tien trinh con lai
echo [!] Crawler chua tu dung sau %GRACE_SECONDS%s. Dang force stop cac tien trinh con lai...
%PS_CMD% -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match '%MATCH_EXPR%') }; foreach ($proc in $procs) { try { Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop; Write-Output ('[OK] Da tat PID ' + $proc.ProcessId) } catch { Write-Output ('[!] Khong the tat PID ' + $proc.ProcessId + ': ' + $_.Exception.Message) } }"
goto :done

:stopped_gracefully
echo [OK] Crawler da nhan STOP.flag va tu dung an toan.

:done
echo.
echo Da hoan tat thao tac dung crawler.
echo De tiep tuc, chay lai START.bat
echo.

pause
