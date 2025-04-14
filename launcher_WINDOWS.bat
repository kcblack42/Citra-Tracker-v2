@echo OFF
@REM Windows launcher for the citra tracker

@REM Change directory to the launcher file directory
pushd "%~dp0"
cd /d "%~dp0"

@REM Run the version check script to test if 3.12 is installed
call python util\python-version-check.py

@REM ERROR LEVELS: 0 - Success, 1 - Fail (python not found), 2 - Fail (incorrect python version), 9009 - Windows 11 being dumb probably
if %ERRORLEVEL%==9009 (
   @REM Windows 11 throws a 9009 instead of 1 if the dummy python exe is ran instead (thanks Microsoft)
   echo Python is not installed.
   echo Python 3.12 is required to run the tracker. Install from https://www.python.org/
   echo Make sure to check the "Add python.exe to PATH" box in the installer.
   echo You may also need to turn off python under App execution aliases in your Windows settings, these are dummy Python files Windows comes with and can block the installed version from python.org
) else if %ERRORLEVEL%==1 (
   @REM Python not found on PATH
   echo Python is not installed or the PATH was not set during installation.
   echo Python 3.12 is required to run the tracker. Install from https://www.python.org/
   echo Make sure to check the "Add python.exe to PATH" box in the installer.
   echo If you are on Windows 11, you may also need to turn off python under App execution aliases in your Windows settings.
) else if %ERRORLEVEL%==0 (
   @REM Run the tracker
   echo Launching the Citra Tracker...
   call python citra-updater.py
)

echo Press any key to exit...
pause>nul