import json
import os
import pathlib
import shutil
from datetime import datetime

# clearing the notes
def notesclear():
    trackadd=r"trackerdata.json"
    trackdata=json.load(open(trackadd,"r+"))
    for mon in trackdata:
        for n in range(0,6):
            trackdata[mon]["stats"][n]=' '
        trackdata[mon]["notes"]=""
        trackdata[mon]["levels"]=[]
        trackdata[mon]["moves"]={}
        trackdata[mon]["abilities"]=[]
    with open(trackadd,'w') as f:
        json.dump(trackdata,f)

    try:
        settingsfile=r"settings.json"
        settingsdict=json.load(open(settingsfile,"r+"))
    except Exception as e:
        print(e)
        with open('errorlog.txt','a+') as f:
            errorLog = str(datetime.now())+": "+str(e)+'\n'
            f.write(errorLog)
        print('Please set up your folders in settings before attempting this.')


    # doing all of the file editing stuff to automatically move to next seed
    try:
        mod_folder = pathlib.Path(str(settingsdict['mod_path']).strip())
        batch_folder = pathlib.Path(str(settingsdict['batch_path']).strip())
        prefix = str(settingsdict['prefix']).strip()

        try:
            curr_seed = int(open('seed.txt', 'r').read())
        except Exception as e:
            # if no seed file present, this is likely the first seed being played.
            print('No seed file found - setting seed counter to 1 and creating file.')
            curr_seed = 1
        
        next_seed = curr_seed + 1

        # copy next seed's files to new folder
        next_folder = batch_folder / '{}{}'.format(prefix, str(next_seed))
        if os.path.exists(next_folder) and os.path.isdir(next_folder):
            shutil.copytree(next_folder, mod_folder, dirs_exist_ok=True)

        # delete files from current seed if they're still there (the last played seed)
        curr_folder = batch_folder / '{}{}'.format(prefix, str(curr_seed))
        if os.path.exists(curr_folder) and os.path.isdir(curr_folder):
            shutil.rmtree(curr_folder)
        try:
            (batch_folder / '{}{}.log'.format(prefix, str(curr_seed))).unlink()
        except Exception as e:
            print('log not found')
            print(e)
        print('previous files deleted')
    except Exception as e:
        print(e)
        with open('errorlog.txt','a+') as f:
            errorLog = str(datetime.now())+": "+str(e)+'\n'
            f.write(errorLog)

    # update seed
    new_seed = open('seed.txt', 'w+').write(str(next_seed))
    print(open('seed.txt', 'r').read())

    # time.sleep(5)
    return next_seed
