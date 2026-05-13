@echo off
echo Starting Quivrr AU inventory refresh WebJob
echo Current directory: %CD%
echo HOME: %HOME%

cd /d "%HOME%\site\wwwroot"

python -u scripts\run_nightly_inventory_refresh.py

echo Quivrr AU inventory refresh WebJob finished with exit code %ERRORLEVEL%

exit /b %ERRORLEVEL%
