@echo OFF
@REM Windows launcher for the citra tracker

@REM Run the version check script to test if 3.12 is installed
call python util\python-version-check.py 2> nul

@REM ERROR LEVELS: 0 - Success, 1 - Fail (python not found), 2 - Fail (incorrect python version)
if %ERRORLEVEL%==1 (
   @REM Python not found on PATH
   echo Python is not installed or the PATH was not set during installation.
   echo Python 3.12 is required to run the tracker. Install from https://www.python.org/
   echo Make sure to check the "Add python.exe to PATH" box in the installer.
) else if %ERRORLEVEL%==0 (
   @REM Run the tracker
   echo Launching the Citra Tracker...
   call python citra-updater.py
)

echo Press any key to exit...
pause>nul