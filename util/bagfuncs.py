def bagitems(c, game, pkmn, items, badgeaddress):
    try:
        #stored as items, key items, tms, medicine, berries
        hphl={"total":0,"percent":0}
        statushl={"total":0}
        pphl={"total":0}
        if game=="X/Y":
            itmdl=[147236508,9952,10208,10640,11016,12616,0x67E852C]   #70F62C #67E892C xy trainers
        elif game=="OmegaRuby/AlphaSapphire":
            itmdl=[147250640,9952,10208,10640,11024,12624] #reverse-berries,meds,tms,keys,items
        elif game=='Sun/Moon': # don't have bag info for gen 7 yet
            return 0, 0, 0, 0
        elif game=='UltraSun/UltraMoon':
            return 0, 0, 0, 0
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[5],2),"little")) #items
        #print(int.from_bytes(c.read_memory(itmdl[0]-itmdl[4],2),"little")) #key items
        #print(str(c.read_memory(147236508-0x67E892C,100),"utf-8")) #0x71A500 oras
        moneyval=int.from_bytes(c.read_memory(itmdl[0],2),"little")
        for item in range(0,100):   #heals, up to 100 also covers first 36 berries
            memread_itemid = int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+(item*4),2),"little")
            memread_itemct = int.from_bytes(c.read_memory(itmdl[0]-itmdl[2]+2+(item*4),2),"little")
            memread_badgect = int.from_bytes(c.read_memory(badgeaddress,2),"little")
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
            badgect = memread_badgect
        # print(hphl,statushl,pphl)
        return hphl, statushl, pphl, badgect
    except:
        if game in ('X/Y', 'OmegaRuby/AlphaSapphire'):
            print("Bag not read")
            return 0, 0, 0