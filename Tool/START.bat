@echo off
setlocal EnableDelayedExpansion
REM ========================================
REM  TOOL CAO BAO TOC DO CAO - AUTO RUN
REM ========================================

cd /d "%~dp0"

set "PYTHON_CMD="

echo.
echo ========================================
echo   TOOL CAO BAO TOC DO CAO
echo ========================================
echo.

REM Xoa file STOP.flag cu (neu con ton tai)
if exist "%~dp0STOP.flag" del "%~dp0STOP.flag"

REM Kiem tra Python
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [!] Loi: Khong tim thay Python 3!
    echo [!] Hay cai Python 3 va tick them tuy chon "Add Python to PATH".
    echo [!] Link tai: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [+] Da phat hien Python!
call %PYTHON_CMD% --version
echo.

REM Dam bao pip san sang
call %PYTHON_CMD% -m ensurepip --upgrade >nul 2>&1
call %PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1

REM ==== Cai dat nhanh cac thu vien can thiet (chi cai khi thieu) ====
set PKGS=newspaper3k lxml_html_clean beautifulsoup4 requests lxml nltk tldextract pandas
for %%p in (%PKGS%) do (
    call %PYTHON_CMD% -m pip show %%p >nul 2>&1
    if errorlevel 1 (
        echo [*] Dang cai %%p ...
        call %PYTHON_CMD% -m pip install --prefer-binary --quiet %%p
    ) else (
        echo [*] Da co %%p
    )
)
echo [*] Tai du lieu NLTK toi thieu...
call %PYTHON_CMD% -m nltk.downloader -q punkt punkt_tab averaged_perceptron_tagger perluniprops nonbreaking_prefixes >nul 2>&1
echo.

REM Kiem tra file main.py ton tai truoc khi chay
if not exist "%~dp0main.py" (
    echo [!] Loi: Khong tim thay main.py trong thu muc tool.
    pause
    exit /b 1
)

REM ==== Tham so mac dinh: cào TẤT CẢ nguồn & TẤT CẢ chuyên mục ====
set "SRC=all"
set "CAT="
set "DEFAULT_MAX=0"
if not "%~1"=="" (
    set "MAX=%~1"
) else (
    set "MAX_INPUT="
    set /p "MAX_INPUT=Nhap so bai toi da moi chuyen muc ^(Enter=0 = lay het tat ca^): "
    if not defined MAX_INPUT (
        set "MAX=%DEFAULT_MAX%"
    ) else (
        set "MAX=!MAX_INPUT!"
    )
)

echo(!MAX!| findstr /r "^[0-9][0-9]*$" >nul
if errorlevel 1 set "MAX=%DEFAULT_MAX%"

echo.
echo [+] Bat dau chay: TAT CA NGUON ^| tat ca chuyen muc ^| max=!MAX!
echo.

REM Chay crawler chinh (all sources, all categories)
call %PYTHON_CMD% "%~dp0main.py" --sources !SRC! --max !MAX!

if errorlevel 1 (
    echo.
    echo [!] Co loi khi chay crawler. Hay kiem tra thong bao o tren.
    pause
    exit /b 1
)

echo.
pause
