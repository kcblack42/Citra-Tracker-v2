import sys
# Version number tuple required to run the tracker
min_python_version = (3,12)
# Check the installed version of python
run_ver = (sys.version_info[0], sys.version_info[1])
if run_ver < min_python_version:
    print(f"The installed python version ({'.'.join(map(str,run_ver + (sys.version_info[2],)))}) is incompatible with the tracker.")
    print(f"You need to install python {'.'.join(map(str,min_python_version))} or later from https://www.python.org/")
    # Exit with code 2 to be distinct to the launcher from when python is not on PATH
    sys.exit(2)