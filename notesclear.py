import json
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