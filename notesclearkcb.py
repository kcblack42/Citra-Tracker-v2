import json
import pathlib
import shutil
import time

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

    # doing all of the file editing stuff to automatically move to next seed
    mod_folder = pathlib.Path('C:/Users/Gordon/AppData/Roaming/Citra/load/mods/')
    batch_folder = pathlib.Path('D:/Games/Pokemon/Ironmon/Ironmon Randomizer/X Batches/')
    seed = open('seed.txt', 'r').read()

    # copy files to new folder
    shutil.copytree(batch_folder / 'kaizo{}'.format(seed), mod_folder, dirs_exist_ok=True)

    # delete files from last seed if they're still there
    try:
        shutil.rmtree(batch_folder / 'kaizo{}'.format(str(int(seed)-1)))
        (batch_folder / 'kaizo{}.log'.format(str(int(seed)-1))).unlink()
        print('previous files deleted')
    except:
        print('structure does not exist')

    # update seed
    new_seed = open('seed.txt', 'w').write(str(int(seed)+1))
    print(open('seed.txt', 'r').read())

    # time.sleep(5)