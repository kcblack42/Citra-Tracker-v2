import json
import pathlib
import shutil
import datetime

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

        seed = open('seed.txt', 'r').read()

        # copy files to new folder
        shutil.copytree(batch_folder / '{}{}'.format(prefix, seed), mod_folder, dirs_exist_ok=True)

        # delete files from last seed if they're still there
        shutil.rmtree(batch_folder / '{}{}'.format(prefix, str(int(seed)-1)))
        try:
            (batch_folder / '{}{}.log'.format(prefix, str(int(seed)-1))).unlink()
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
    new_seed = open('seed.txt', 'w+').write(str(int(seed)+1))
    print(open('seed.txt', 'r').read())

    # time.sleep(5)
    return seed
