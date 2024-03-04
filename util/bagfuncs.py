import json

def bagload():
    try:
        bag=r"bagitems.json"
        bagitems=json.load(open(bag,"r+"))
    except:
        bagitems = {
            'healing':{
                'full restore':0, 
                'max potion':0, 
                'hyper potion':0, 
                'energy root':0, 
                'moomoo milk':0, 
                'lemonade':0, 
                'soda pop':0, 
                'super potion':0, 
                'fresh water':0, 
                'energy powder':0, 
                'potion':0, 
                'rage candy bar':0, 
                'berry juice':0, 
                'sweet heart':0
            }, 
            'status':{
                'full restore':0, 
                'full heal':0, 
                'heal powder':0, 
                'lava cookie':0, 
                'old gateau':0, 
                'casteliacone':0, 
                'lumiose galette':0, 
                'shalour sable':0, 
                'big malasada':0,
                'antidote':0, 
                'paralyze heal':0, 
                'burn heal':0, 
                'ice heal':0, 
                'awakening':0
            }, 
            'pp':{
                'max elixir':0, 
                'elixir':0, 
                'max ether':0, 
                'ether':0, 
                'leppa berry':0
            }
        }
    return bagitems

def bagitems(c, game, pkmn, items):
    try:
        #stored as items, key items, tms, medicine, berries
        hphl={"total":0,"percent":0}
        statushl={"total":0}
        pphl={"total":0}
        if game=="X/Y":
            itmdl=[147236508,9952,10208,10640,11016,12616,0x67E852C]   #70F62C #67E892C xy trainers
        if game=="OmegaRuby/AlphaSapphire":
            itmdl=[147250640,9952,10208,10640,11024,12624] #reverse-berries,meds,tms,keys,items
        #print(int.from_bytes(c.read_memory(itmdl[0],2),"little")) #money
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[5],2),"little")) #items
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[4],2),"little")) #key items
        #print(str(c.read_memory(147236508-0x67E892C,100),"utf-8")) #0x71A500 oras
        for item in range(0,100):   #heals, up to 100 also covers first 36 berries
            if int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little")!=0:
                if "heal" not in items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))].keys():
                    continue
                #print(items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["name"],str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")))
                if items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["type"]=="status":
                    statushl['total']=statushl["total"]+int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    statushl[items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["name"]]=int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                if items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["type"]=="pp":
                    pphl['total']=pphl["total"]+int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    pphl[items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["name"]]=int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                if items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["type"]=="per":
                    hphl['total']=hphl["total"]+int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    hphl[items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["name"]]=int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    hphl['percent']=str(round(int(hphl['percent'])+(int(items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["value"])*int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little"))))
                if items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["type"]=="set":
                    hphl['total']=hphl["total"]+int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    hphl[items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["name"]]=int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
                    if int(items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["value"])<pkmn.maxhp:
                        hphl['percent']=str(round(int(hphl['percent'])+(int(items[str(int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little"))]["heal"]["value"])*int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")*100/pkmn.maxhp)))
                    else:
                        hphl['percent']=str(int(hphl['percent'])+100)
        # print(hphl["Super Potion"])
        try:
            if moneyval-int.from_bytes(c.read_memory(itmdl[0],2),"little")==700 and hphl["Super Potion"]-1==superval:
                pcount+=1
        except:
            pcount=0
        moneyval=int.from_bytes(c.read_memory(itmdl[0],2),"little")
        try:
            superval=hphl["Super Potion"]
        except:
            pcount=0
        # print(hphl,statushl,pphl)
        return hphl, statushl, pphl
    except:
        if game in ('X/Y', 'OmegaRuby/AlphaSapphire'):
            print("Bag not read")