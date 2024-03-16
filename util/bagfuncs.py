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
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[5],2),"little")) #items
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[4],2),"little")) #key items
        #print(str(c.read_memory(147236508-0x67E892C,100),"utf-8")) #0x71A500 oras
        moneyval=int.from_bytes(c.read_memory(itmdl[0],2),"little")
        for item in range(0,100):   #heals, up to 100 also covers first 36 berries
            memread_itemid = int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little")
            memread_itemct = int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
            # print(memread_itemid, ';;;', items[str(memread_itemid)]["name"], ';;;', memread_itemct)
            if memread_itemid!=0:
                if "heal" not in items[str(memread_itemid)].keys():
                    continue
                #print(items[str(memread_itemid)]["name"],str(memread_itemct))
                if items[str(memread_itemid)]["heal"]["type"]=="status":
                    statushl['total']=statushl["total"]+memread_itemct
                    statushl[items[str(memread_itemid)]["name"]]=memread_itemct
                if items[str(memread_itemid)]["heal"]["type"]=="pp":
                    pphl['total']=pphl["total"]+memread_itemct
                    pphl[items[str(memread_itemid)]["name"]]=memread_itemct
                if items[str(memread_itemid)]["heal"]["type"]=="per":
                    hphl['total']=hphl["total"]+memread_itemct
                    hphl[items[str(memread_itemid)]["name"]]=memread_itemct
                    hphl['percent']=str(round(int(hphl['percent'])+(int(items[str(memread_itemid)]["heal"]["value"])*memread_itemct)))
                if items[str(memread_itemid)]["heal"]["type"]=="set":
                    hphl['total']=hphl["total"]+memread_itemct
                    hphl[items[str(memread_itemid)]["name"]]=memread_itemct
                    if int(items[str(memread_itemid)]["heal"]["value"])<pkmn.maxhp:
                        hphl['percent']=str(round(int(hphl['percent'])+(int(items[str(memread_itemid)]["heal"]["value"])*memread_itemct*100/pkmn.maxhp)))
                    else:
                        hphl['percent']=str(int(hphl['percent'])+100*memread_itemct)
        # print(hphl,statushl,pphl)
        return hphl, statushl, pphl
    except:
        if game in ('X/Y', 'OmegaRuby/AlphaSapphire'):
            print("Bag not read")
            return 0, 0, 0