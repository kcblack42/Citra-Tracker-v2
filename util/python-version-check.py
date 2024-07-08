import sys
min_python_version = (3,12)
run_ver = (sys.version_info[0], sys.version_info[1])
print (run_ver)
if run_ver < min_python_version:
    print(f"The installed python version ({'.'.join(map(str,run_ver + (sys.version_info[2],)))}) is incompatible.")
    print(f"You need to install python {'.'.join(map(str,min_python_version))}.0 or later to run the citra tracker.")
    exit(1)

###### DEBUG - for testing, remove later
print("ALL GOOD")
######
exit(0)