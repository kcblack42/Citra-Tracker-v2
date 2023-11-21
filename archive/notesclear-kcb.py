import json
trackadd=r"trackerdata-kcb.json"
trackdata=json.load(open(trackadd,"r+"))
for mon in trackdata:
    # for n in range(0,3):
    #     trackdata[mon]["abilities"][n]=""
    for n in range(0,6):
        trackdata[mon]["stats"][n]=" "
    trackdata[mon]["abilities"]=[]
    trackdata[mon]["notes"]=""
    trackdata[mon]["levels"]=[]
    trackdata[mon]["moves"]={}
with open(trackadd,'w') as f:
    json.dump(trackdata,f)