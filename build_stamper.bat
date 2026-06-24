@echo off
REM ============================================================
REM  ShashevPro Stamper - build single-file EXE with icon
REM  Requires PyInstaller:   pip install pyinstaller
REM  Put icon.ico next to this file and sp_stamper.py
REM ============================================================

pyinstaller --onefile --windowed --noconfirm --clean --name "SP_Stamper" --icon "icon.ico" --add-data "icon.ico;." sp_stamper.py

echo.
echo Build finished. Find SP_Stamper.exe in the "dist" folder.
pause
