@echo off
cd /d "%~dp0"
where pyw >nul 2>&1 && (start "" pyw -3 dd_parche_gui.py & exit /b)
where pythonw >nul 2>&1 && (start "" pythonw dd_parche_gui.py & exit /b)
py -3 dd_parche_gui.py
