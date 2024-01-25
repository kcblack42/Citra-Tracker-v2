import json
import pathlib
import shutil

# clearing the notes
def notesclear(settings):
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

    path = {}
    with open(settings) as f:
        for line in f:
            name, value = line.split('=')
            path[name] = str(value)

    # doing all of the file editing stuff to automatically move to next seed
    try:
        mod_folder = pathlib.Path(path['mod_path'])
        batch_folder = pathlib.Path(path['batch_path'])
        prefix = path['prefix']
    except:
        print('Invalid folder location.')
        
    try:
        seed = open('seed.txt', 'r').read()
    except:
        seed = 1

    # copy files to new folder
    shutil.copytree(batch_folder / '{}{}'.format(prefix, seed), mod_folder, dirs_exist_ok=True)

    # delete files from last seed if they're still there
    try:
        shutil.rmtree(batch_folder / '{}{}'.format(prefix, str(int(seed)-1)))
        (batch_folder / 'kaizo{}.log'.format(str(int(seed)-1))).unlink()
        print('previous files deleted')
    except:
        print('structure does not exist')

    # update seed
    new_seed = open('seed.txt', 'w+').write(str(int(seed)+1))
    print(open('seed.txt', 'r').read())

    # time.sleep(5)
    return seed
