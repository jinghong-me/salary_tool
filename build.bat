@echo off
chcp 65001 >nul
echo ==========================================
echo  Salary Tool v2.0 - Build Script
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

:: Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt -q

:: Install PyInstaller
echo [2/4] Installing PyInstaller...
pip install pyinstaller pillow -q

:: Convert icon
echo [3/4] Preparing icon...
python -c "from PIL import Image; img = Image.open('icon.png'); img.save('icon.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])" 2>nul

:: Build
echo [4/4] Building executable...
pyinstaller --onefile --windowed --name "SalaryTool" --icon=icon.ico --add-data="icon.ico;." --clean --noconfirm --hidden-import=pandas --hidden-import=openpyxl --hidden-import=tkinter salary_tool.py

if errorlevel 1 (
    echo Build failed, trying without icon...
    pyinstaller --onefile --windowed --name "SalaryTool" --clean --noconfirm salary_tool.py
)

:: Create distribution
echo.
echo [5/5] Creating distribution package...
if exist "SalaryTool_v2.0" rd /s /q "SalaryTool_v2.0"
mkdir "SalaryTool_v2.0"
copy dist\SalaryTool.exe "SalaryTool_v2.0\" >nul
copy README.md "SalaryTool_v2.0\" >nul
copy icon.png "SalaryTool_v2.0\" >nul
if exist icon.ico copy icon.ico "SalaryTool_v2.0\" >nul

echo @echo off > "SalaryTool_v2.0\start.bat"
echo start "" "SalaryTool.exe" >> "SalaryTool_v2.0\start.bat"

powershell -Command "Compress-Archive -Path 'SalaryTool_v2.0' -DestinationPath 'SalaryTool_v2.0.zip' -Force"

echo.
echo ==========================================
echo  Build Complete!
echo ==========================================
echo.
echo Output files:
echo   - Executable: dist\SalaryTool.exe
echo   - Package: SalaryTool_v2.0.zip
echo.
pause
