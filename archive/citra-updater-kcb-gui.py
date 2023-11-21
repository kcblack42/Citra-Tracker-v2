import struct
import time
import os
import subprocess
import json
import sqlite3
import threading
import traceback
from configparser import ConfigParser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler
import logging
from citra import Citra

# newly added kcb
import re
import os
from urllib.request import urlopen, Request
from io import BytesIO
import PySimpleGUI as sg
try:
    from PIL import Image
except ImportError:
    import Image

# pysimplegui settings et al
track_title = 'Ironmon Tracker'
scale = 1.3
track_size = (600, 600)
sg.set_options(font=('Franklin Gothic Medium', 16), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', 14), tooltip_time=200, scaling=scale)

trackadd=r"trackerdata.json"

def crypt(data, seed, i):
    value = data[i]
    shifted_seed = seed >> 16
    shifted_seed &= 0xFF
    value ^= shifted_seed
    result = struct.pack("B", value)

    value = data[i + 1]
    shifted_seed = seed >> 24
    shifted_seed &= 0xFF
    value ^= shifted_seed
    result += struct.pack("B", value)

    return result

def crypt_array(data, seed, start, end):
    result = bytes()
    temp_seed = seed

    for i in range(start, end, 2):
        temp_seed *= 0x41C64E6D
        temp_seed &= 0xFFFFFFFF
        temp_seed += 0x00006073
        temp_seed &= 0xFFFFFFFF
        result += crypt(data, temp_seed, i)

    return result

def shuffle_array(data, sv, block_size):
    block_position = [[0, 0, 0, 0, 0, 0, 1, 1, 2, 3, 2, 3, 1, 1, 2, 3, 2, 3, 1, 1, 2, 3, 2, 3],
                      [1, 1, 2, 3, 2, 3, 0, 0, 0, 0, 0, 0, 2, 3, 1, 1, 3, 2, 2, 3, 1, 1, 3, 2],
                      [2, 3, 1, 1, 3, 2, 2, 3, 1, 1, 3, 2, 0, 0, 0, 0, 0, 0, 3, 2, 3, 2, 1, 1],
                      [3, 2, 3, 2, 1, 1, 3, 2, 3, 2, 1, 1, 3, 2, 3, 2, 1, 1, 0, 0, 0, 0, 0, 0]]
    result = bytes()
    for block in range(4):
        start = block_size * block_position[block][sv]
        end = start + block_size
        result += data[start:end]
    return result

def decrypt_data(encrypted_data):
    pv = struct.unpack("<I", encrypted_data[:4])[0]
    sv = ((pv >> 0xD) & 0x1F) % 24

    start = 8
    end = (4 * BLOCK_SIZE) + start

    header = encrypted_data[:8]

    # Blocks
    blocks = crypt_array(encrypted_data, pv, start, end)

    # Stats
    stats = crypt_array(encrypted_data, pv, end, len(encrypted_data))

    final_result = header + shuffle_array(blocks, sv, BLOCK_SIZE) + stats

    return final_result

class Pokemon:
    def __init__(self, encrypted_data):
        first_byte = encrypted_data[0]
        if first_byte != 0:
            self.raw_data = decrypt_data(encrypted_data)
        else:
            self.raw_data = ""

    def species_num(self):
        if len(self.raw_data) > 0:
            return struct.unpack("<H", self.raw_data[0x8:0xA])[0]
        else:
            return 0

    def getAtts(self,gamegroupid,gen):
        dex = self.species_num()
        form = struct.unpack("B",self.raw_data[0x1D:0x1E])[0]
        query = f"""select pokemonid from "pokemon.pokemon" where pokemonpokedexnumber = {dex}"""
        print("form",form,"dex",dex)
        match dex:
            #bit 0: fateful encounter flag
            #bit 1: female-adds 2 to resulting form variable, so 2 or 10 instead of 0 or 8
            #bit 2: genderless-adds 4, so 4 or 12
            #bits 3-7: form change flags-8 typical starting point then increases by 8, so 8, 16, 24, etc
            case 641 | 642 | 645:
                if form > 0: ### Therian forms of Tornadus, Thundurus, Landorus
                    query+= " and pokemonsuffix = 'therian'"
            case 6: #Charizard
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'mega-x'"
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'mega-y'"
            case 150: ### Mewtwo
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'mega-x'"
                    case 20: ### Mewtwo Y
                        query+= " and pokemonsuffix = 'mega-y'"
            case 201: ### Unown
                query+= " and pokemonsuffix is null"
            case 351: ### Castform
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'sunny'"
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'rainy'"
                    case 24 | 26:
                        query+= " and pokemonsuffix = 'snowy'"
            case 382: ### Kyogre
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'primal'"
            case 383: ### Groudon
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'primal'"
            case 386: ### Deoxys
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'attack'"
                    case 20:
                        query+= " and pokemonsuffix = 'defense'"
                    case 28:
                        query+= " and pokemonsuffix = 'speed'"
            case 413: ### Wormadam
                match form:
                    case 10:
                        query+= " and pokemonsuffix = 'sandy'"
                    case 18:
                        query+= " and pokemonsuffix = 'trash'"
                    case 2:
                        query+= " and pokemonsuffix = 'plant'"
            case 421: ### Cherrim
                query+= " and pokemonsuffix is null"
            case 422: ### Shellos
                query+= " and pokemonsuffix is null"
            case 423: ### Gastrodon
                query+= " and pokemonsuffix is null"
            case 479: ### Rotom
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'heat'"
                    case 20:
                        query+= " and pokemonsuffix = 'wash'"
                    case 28:
                        query+= " and pokemonsuffix = 'frost'"
                    case 36:
                        query+= " and pokemonsuffix = 'fan'"
                    case 44:
                        query+= " and pokemonsuffix = 'mow'"
            case 487: ### Giratina
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'origin'"
            case 492: ### Shaymin
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'sky'"
            case 555: ### Darmanitan
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'zen'"
            case 585: ### Deerling
                query+= " and pokemonsuffix is null"
            case 586: ### Sawsbuck
                query+= " and pokemonsuffix is null"
            case 646: ### Kyurem
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'white'"
                match form:
                    case 20:
                        query+= " and pokemonsuffix = 'black'"
            case 647: ### Keldeo
                query+= " and pokemonsuffix is null"
            case 648: ### Meloetta
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'pirouette'"
                    case 4: #base form lmao
                        query+= " and pokemonsuffix = 'aria'"
            case 649: ### Genesect
                query+= " and pokemonsuffix is null"
            case 658: ### Greninja
                match form:
                    case 8 | 16:
                        query+= " and pokemonsuffix = 'ash'"
            case 666: ### Vivillon
                query+= " and pokemonsuffix is null"
            case 669: ### Flabébé
                query+= " and pokemonsuffix is null"
            case 670: ### Floette
                match form:
                    case 42: #0 8 16 24 32 40
                        query+= " and pokemonsuffix = 'eternal'"
                    case _:
                        query+= " and pokemonsuffix is null"
            case 671: ### Florges
                query+= " and pokemonsuffix is null"
            case 676: ### Furfrou
                query+= " and pokemonsuffix is null"
            case 678: ### Meowstic
                match form:
                    case 10:
                        query+= " and pokemonsuffix = 'f'"
            case 681: ### Aegislash
                match form:
                    case 0 | 2:
                        query+= " and pokemonsuffix = 'shield'"
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'blade'"
            case 711: ### Gourgeist
                match form:
                    case 16:
                        query+= " and pokemonsuffix = 'average'"
            case 716: ### Xerneas
                query+= " and pokemonsuffix is null"
            case 718: ### Zygarde only needed for gen 7
                match form:
                    case 12:
                        query+= " and pokemonsuffix = '10'"
                    case 20 | 36:
                        query+= " and pokemonsuffix = 'complete'"
            case 720: ### Hoopa
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'unbound'"
            case 741: ### Oricorio
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'pom-pom'"
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'pau'"
                    case 24 | 26:
                        query+= " and pokemonsuffix = 'sensu'"
            case 745: ### Lycanroc
                match form:
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'dusk'"
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'midnight'"
            case 746: ### Wishiwashi
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'school'"
            case 774: ### Minior 4 12 20 28 36 44 52 60
                match form:
                    case 12 | 20 | 28 | 36 | 44 | 52 | 60: #60 is red
                        query+= " and pokemonsuffix = 'core'"
            case 778: ### Mimikyu
                query+= " and pokemonsuffix is null"
            case 800: ### Necrozma
                match form:
                    case 12:
                        query+= " and pokemonsuffix = 'dusk'"
                    case 20:
                        query+= " and pokemonsuffix = 'dawn'"
                    case 28:
                        query+= " and pokemonsuffix = 'ultra'"
            case 801: ### Magearna
                query+= " and pokemonsuffix is null"
            # case alolan forms-none have separate forms so just case them for if their form > 0
            case 81 | 82 | 100 | 101 | 120 | 121 | 137 | 233 | 292 | 337 | 338 | 343 | 344 | 374 | 375 | 376 | 436 | 437 | 462 | 474 | 489 | 490 | 599 | 600 | 601 | 615 | 622 | 623 | 703 | 774 | 781 | 854 | 855 | 770 | 132 | 144 | 145 | 146 | 201 | 243 | 244 | 245 | 249 | 250 | 251 | 377 | 378 | 379 | 382 | 383 | 384 | 385 | 386 | 480 | 481 | 482 | 483 | 484 | 486 | 491 | 493 | 494 | 638 | 639 | 640 | 643 | 644 | 646 | 647 | 649 | 716 | 717 | 718 | 719 | 721: ### Genderless exceptions
                query+= " and pokemonsuffix is null"
            case _:
                if form == 2:
                    query+= " and pokemonsuffix is null"
                elif form > 0:
                    query+= " and pokemonsuffix ='mega'"
                else:
                    query+= " and pokemonsuffix is null"
        print(query)
        self.id = cursor.execute(query).fetchone()[0]
        self.species,self.suffix,self.name = cursor.execute(f"""select pokemonspeciesname,pokemonsuffix,pokemonname from "pokemon.pokemon" where pokemonid = {self.id}""").fetchone()
        self.suffix = self.suffix or ''
        # self.name = self.name.replace(' Form','').replace(' Cloak','')
        self.spritename = self.species.lower()+('' if self.suffix == '' else ('-'+self.suffix))
        self.spriteurl = "https://img.pokemondb.net/sprites/"+getURLAbbr(gamegroupid)+"/normal/"+self.spritename+".png"
        self.bst = cursor.execute(f"""select
                                sum(pokemonstatvalue)
                            from "pokemon.pokemonstat"
                                where pokemonid = {self.id}
                                and generationid = (
                                    select
                                        max(generationid)
                                    from "pokemon.pokemonstat"
                                        where generationid <= {gen}
                                )""").fetchone()[0]    
        self.types = cursor.execute(f"""
                               select
                                    ty.typename
                                from "pokemon.pokemontype" pt
                                    left join "pokemon.type" ty on pt.typeid = ty.typeid
                                where pt.pokemonid = {self.id} and pt.generationid = {gen}                              
                               """).fetchall()
        self.types = [type for type in self.types]
        self.held_item_num=str(struct.unpack("<H", self.raw_data[0xA:0xC])[0])
        self.held_item_name = items[self.held_item_num]['name'].replace("é","&#233;")
        self.ability_num = struct.unpack("B", self.raw_data[0x14:0x15])[0] # Ability
        query = f"""select
                        ab.abilityname
                        ,abilitydescription
                    from "pokemon.generationability" ga
                        left join "pokemon.ability" ab on ga.abilityid = ab.abilityid
                        left join "pokemon.abilitylookup" al on ab.abilityname = al.abilityname
                    where al.abilityindex = {self.ability_num} and ga.generationid <= {gen}
                    order by ga.generationid desc
                    """
        self.abilityname,self.abilitydescription = cursor.execute(query).fetchone()
        self.ability = {'name':self.abilityname,'description':self.abilitydescription}
        self.nature_num = struct.unpack("B", self.raw_data[0x1C:0x1D])[0] ## Nature
        self.nature = cursor.execute(f"""select
                        n.naturename
                    from "pokemon.nature" n
                        left join "pokemon.naturelookup" nl on n.naturename = nl.naturename
                    where nl.natureindex = {self.nature_num}
                    """).fetchone()[0]
        self.friendship = struct.unpack("B", self.raw_data[0xCA:0xCB])[0] ### Friendship
        self.level_met = struct.unpack("<H", self.raw_data[0xDD:0xDF])[0] ####### Level met
        self.level = struct.unpack("B", self.raw_data[0xEC:0xED])[0] ### Current level
        self.cur_hp = struct.unpack("<H", self.raw_data[0xF0:0xF2])[0] ####### Current HP
        self.maxhp = struct.unpack("<H", self.raw_data[0xF2:0xF4])[0] ## Max HP
        self.attack = struct.unpack("<H", self.raw_data[0xF4:0xF6])[0] ## Attack stat
        self.defense = struct.unpack("<H", self.raw_data[0xF6:0xF8])[0] ## Defense stat
        self.speed = struct.unpack("<H", self.raw_data[0xF8:0xFA])[0] ## Speed stat
        self.spatk = struct.unpack("<H", self.raw_data[0xFA:0xFC])[0] ## Special attack stat
        self.spdef = struct.unpack("<H", self.raw_data[0xFC:0xFE])[0] ## Special defense stat
        self.evhp = struct.unpack("B", self.raw_data[0x1E:0x1F])[0]
        self.evattack = struct.unpack("B", self.raw_data[0x1F:0x20])[0]
        self.evdefense = struct.unpack("B", self.raw_data[0x20:0x21])[0]
        self.evspeed = struct.unpack("B", self.raw_data[0x21:0x22])[0]
        self.evspatk = struct.unpack("B", self.raw_data[0x22:0x23])[0]
        self.evspdef = struct.unpack("B", self.raw_data[0x23:0x24])[0]
        self.ivloc = struct.unpack("<I", self.raw_data[0x74:0x78])[0]
        self.ivhp = (self.ivloc >> 0) & 0x1F ############################## HP IV
        self.ivattack = (self.ivloc >> 5) & 0x1F ############################## Attack IV
        self.ivdefense = (self.ivloc >> 10) & 0x1F ############################# Defense IV
        self.ivspeed = (self.ivloc >> 15) & 0x1F ############################# Speed IV
        self.ivspatk = (self.ivloc >> 20) & 0x1F ############################# Special attack IV
        self.ivspdef = (self.ivloc >> 25) & 0x1F ############################# Special defense IV
        def moves(self):
                def movedescription(id):
                    query = f"""select movedescription from "pokemon.generationmove" where generationmoveid = {id}"""
                    return cursor.execute(query).fetchone()[0]
                move1 = ((0x5A,0x5C),(0x62,0x63))
                move2 = ((0x5C,0x5E),(0x63,0x64))
                move3 = ((0x5E,0x60),(0x64,0x65))
                move4 = ((0x60,0x62),(0x65,0x66))
                for ml,pl in (move1,move2,move3,move4):
                    try:
                        move_num = struct.unpack("<H", self.raw_data[ml[0]:ml[1]])[0]
                        query = f"""
                            select
                                mv.movename,
                                gm.generationmoveid,
                                movepp,
                                typename,
                                movepower,
                                moveaccuracy,
                                movecontactflag,
                                movecategoryname
                            from "pokemon.generationmove" gm
                                left join "pokemon.move" mv on gm.moveid = mv.moveid
                                left join "pokemon.movelookup" ml on mv.movename = ml.movename
                                left join "pokemon.type" ty on gm.typeid = ty.typeid
                                left join "pokemon.movecategory" mc on gm.movecategoryid = mc.movecategoryid
                            where ml.moveindex = {move_num} and gm.generationid = {gen}"""
                        movename,id,pp,type,power,acc,contact,category = cursor.execute(query).fetchone()
                        yield {'name':movename,
                            'description':movedescription(id),
                                'pp':struct.unpack("<B",self.raw_data[pl[0]:pl[1]])[0],
                                'maxpp':int(pp),
                                'type':type,
                                'power':power,
                                'acc':acc,
                                'contact':contact,
                                'category':category
                            }
                    except:
                        yield {'name':'',
                               'description':'',
                               'pp':0,
                               'maxpp':0,
                                'type':None,
                                'power':0,
                                'acc':0,
                                'contact':False,
                                'category':None}
                    
        self.moves = [move for move in moves(self)]
        try:
            self.evotype,self.evoitem,self.evolevel,self.evostring,self.evolocation = cursor.execute(f"""
                                            SELECT
                                                evolutiontypename,
                                                itemname,
                                                pokemonevolutionlevel,
                                                pokemonevolutionuniquestring,
                                                locationname
                                            FROM "pokemon.pokemonevolutioninfokaizo" peik
                                                LEFT JOIN "pokemon.item" it ON peik.itemid = it.itemid
                                                LEFT JOIN "pokemon.pokemon" target ON peik.targetpokemonid = target.pokemonid
                                                LEFT JOIN "pokemon.evolutiontype" evot ON peik.evolutiontypeid = evot.evolutiontypeid
                                                LEFT JOIN "pokemon.location" loc ON peik.locationid = loc.locationid
                                                WHERE gamegroupid IN (
                                                    SELECT
                                                        gamegroupid
                                                    FROM "pokemon.gamegroup"
                                                        WHERE gamegrouporder < (
                                                            SELECT
                                                                gamegrouporder
                                                            FROM "pokemon.gamegroup"
                                                                WHERE gamegroupid = '{gamegroupid}'
                                                            )
                                                    )
                                                AND basepokemonid = {str(self.id)}
            """).fetchone()
            self.evo = True
        except:
            self.evo = False
        self.statusbyte = struct.unpack("<B",self.raw_data[0xE8:0xE9])[0] ### Status byte
        match self.statusbyte:
            case 1:
                self.status = 'Paralyzed'
            case 2:
                self.status = 'Asleep'
            case 3:
                self.status = 'Frozen'
            case 4:
                self.status = 'Burned'
            case 5:
                self.status = 'Poisoned'
            case _:
                self.status = ''
        
    def getStatChanges(self):
            raised,lowered = cursor.execute(f"""
            select
                    raisedstat.statname
                    ,loweredstat.statname
                from "pokemon.nature" n
                    left join "pokemon.stat" raisedstat on n.raisedstatid = raisedstat.statid
                    left join "pokemon.stat" loweredstat on n.loweredstatid = loweredstat.statid
                where n.naturename = '{self.nature}'
                """).fetchone()
            for stat in ('Attack','Defense','Special Attack','Special Defense','Speed'):
                if stat == raised:
                    yield 'raised'
                elif stat == lowered:
                    yield 'lowered'
                else:
                    yield ''

    def getMoves(self,gamegroupid):
        learnedcount = 0
        query = f"""
            select
                pokemonmovelevel
            from "pokemon.pokemonmove" pm
                left join "pokemon.pokemonmovemethod" pmm on pm.pokemonmovemethodid = pmm.pokemonmovemethodid
                where gamegroupid = {gamegroupid}
                    and pokemonmovemethodname = 'Level up'
                    and pokemonmovelevel > 1
                    and pokemonid = {self.id}
                order by pokemonmovelevel
        """
        learnlist = cursor.execute(query).fetchall()
        nextmove = None
        totallearn = 0
        learnstr = ''
        for learn in learnlist:
            learnstr+=str(learn[0])+', '
            if int(learn[0]) > 1:
                totallearn+=1
        for learn in learnlist:
            if not int(learn[0]) <= int(self.level):
                nextmove = learn[0]
                break
            elif int(learn[0]) > 1:
                learnedcount+=1
        return totallearn,nextmove,learnedcount,learnstr[0:len(learnstr)-2]

    def getCoverage(self,gen,gamegroupid):
        types = []
        for move in self.moves:
            if move['power']:
                if move['power'] > 0:
                    types.append(move['type'])
        monTypes = f"""
            with montypes as (
                select distinct
                    mon.pokemonid as pokemonid,
                    type1.typeid as type1id,
                    type2.typeid as type2id,
                    pt1.generationid as gen
                from "pokemon.pokemon" mon
                    join "pokemon.pokemontype" pt1 on mon.pokemonid = pt1.pokemonid and pt1.pokemontypeorder = 1 and pt1.generationid = {gen}
                    left join "pokemon.pokemontype" pt2 on mon.pokemonid = pt2.pokemonid and pt2.pokemontypeorder = 2 and pt2.generationid = {gen}
                    join "pokemon.type" type1 on pt1.typeid = type1.typeid
                    left join "pokemon.type" type2 on pt2.typeid = type2.typeid
                    join "pokemon.gamegroup" gg on pt1.generationid = gg.generationid and gg.gamegroupid = {gamegroupid}
                    join "pokemon.game" gm on gg.gamegroupid = gm.gamegroupid
                    join "pokemon.pokemongameavailability" pga on mon.pokemonid = pga.pokemonid and gm.gameid = pga.gameid and pga.gameid
                    ),
        """
        monbsts = f"""
            monbsts as (
                select
                    ps.pokemonid as pokemonid,
                    mt.type1id,
                    mt.type2id,
                    mt.gen,
                    sum(ps.pokemonstatvalue) as bst
                from "pokemon.pokemonstat" ps
                    join montypes mt on ps.generationid = mt.gen AND ps.pokemonid = mt.pokemonid
                    GROUP BY 1,2,3,4
            ),
        """
        attackingdamage = f"""
            attackingdmg as (
                select
                    mb.pokemonid as pokemoeeeeeeenid,
                    mb.type1id as type1id,
                    mb.type2id as type2id,
                    max(tm1.damagemodifier*coalesce(tm2.damagemodifier,1)) as dmgmod
                from monbsts mb
                    join "pokemon.typematchup" tm1 on mb.type1id = tm1.defendingtypeid and tm1.generationid = mb.gen
                    left join "pokemon.typematchup" tm2
                        on mb.type2id = tm2.defendingtypeid
                        and tm1.attackingtypeid = tm2.attackingtypeid
                        and tm2.generationid = mb.gen
                    join "pokemon.type" attackingtype on tm1.attackingtypeid = attackingtype.typeid
                where attackingtype.typename in {str(types).replace('[','(').replace(']',')')}
                group by 1,2,3

            )
        """
        coveragecountsquery = f"""
                select
                    ad.dmgmod,
                    count(ad.pokemonid)
                from attackingdmg ad
                group by 1
                order by 1 asc
        """
        coveragecounts = cursor.execute(monTypes+monbsts+attackingdamage+coveragecountsquery).fetchall()
        # topbstsquery = f"""
        #     select 
        #         mb.bst,
        #         mon.pokemonname
        #     from attackingdmg ad
        #         join monbsts mb on ad.pokemonid = mb.pokemonid
        #         join "pokemon.pokemon" mon on ad.pokemonid = mon.pokemonid
        #     order by ad.dmgmod asc, mb.bst desc limit 10
        # """
        # topbsts = cursor.execute(monTypes+monbsts+attackingdamage+topbstsquery).fetchall()
        return coveragecounts#,topbsts
        

#######################################################################


class Pokemon6(Pokemon):
    def __init__(self, data):
        Pokemon.__init__(self, data)

class Pokemon7(Pokemon):
    def __init__(self, data):
        Pokemon.__init__(self, data)

def getGame(c):
    partylist=[0x8CE1CE8,0x8CF727C,0x34195E10,0x33F7FA44]
    try:
        for item in range(0,4):
            for slot in range(0, 6):
                if read_party(c,partylist[item])[slot].species_num() in range(1,808):
                    namelist=["X/Y","OmegaRuby/AlphaSapphire","Sun/Moon","UltraSun/UltraMoon"]
                    return namelist[item]
    except Exception as e:
        print(e)

def getaddresses(c):
    getGam=getGame(c)
    if getGam=='X/Y':
        partyaddress=0x8CE1CE8
        battlewildpartyadd=142625392
        battlewildoppadd=142622412
        battletrainerpartyadd=142622504
        battletraineroppadd=142625484
        curoppadd=138545352
        wildppadd=136331232
        trainerppadd=136338160
        mongap=580
    elif getGam=='OmegaRuby/AlphaSapphire':
        partyaddress=0x8CF727C
        battlewildpartyadd=0x8CF727C-6000000+812440
        battlewildoppadd=0x8CF727C-6000000+815420
        battletrainerpartyadd=0x8CF727C-6000000+809556
        battletraineroppadd=0x8CF727C-6000000+812536
        curoppadd=0x8CF727C-0xAF2F5C+0x22EA60 #little endian
        wildppadd=0x8CF727C-0xAF2F5C-20 #0x8CF727C-0xAF2F5C
        trainerppadd=0x8CF727C-0xAF2F5C-20+6928
        mongap=580 #Gen 6 has a gap between each mon's data, and goes directly from your mons to the opponent's...
    elif getGam=='Sun/Moon':
        partyaddress=0x34195E10
        battlewildpartyadd=0x34195E10-30000000+5705168
        battlewildoppadd=0x34195E10-30000000+5702188
        battletrainerpartyadd=0x33F7FA44-30000000+7995384
        battletraineroppadd=0x33F7FA44-30000000+7998364
        curoppadd=0x34195E10-68732064+68472752
        wildppadd=0x34195E10-68732064-34
        trainerppadd=0x34195E10-68732064-34
        mongap=816 #while Gen 7 spaces them out, so its 6 slots for your mon, 6 slots for teammates, then 6 slots for enemies.
    elif getGam=='UltraSun/UltraMoon':
        partyaddress=0x33F7FA44
        battlewildpartyadd=0x33F7FA44-30000000+7008668
        battlewildoppadd=0x33F7FA44-30000000+7011648 
        battletrainerpartyadd=0x33F7FA44-30000000+7110648
        battletraineroppadd=0x33F7FA44-30000000+7113628
        curoppadd=0x33F7FA44-0x3f760d4+66286592
        wildppadd=0x33F7FA44-0x3f760d4-34
        trainerppadd=0x33F7FA44-0x3f760d4-34
        mongap=816
    if read_party(c,battlewildoppadd)[0].species_num() in range(1,808) and int.from_bytes(c.read_memory(wildppadd,1))<65:
        return battlewildpartyadd,battlewildoppadd,wildppadd,curoppadd,'w',mongap
    elif read_party(c,battletraineroppadd)[0].species_num() in range(1,808) and int.from_bytes(c.read_memory(trainerppadd,1))<65:
        return battletrainerpartyadd,battletraineroppadd,trainerppadd,curoppadd,'t',mongap
    else:
        return partyaddress,0,0,0,'p',mongap
def cls():
    os.system('cls' if os.name=='nt' else 'clear')

def read_party(c,party_address):
    party = []    
    for i in range(6):
        read_address = party_address + (i * SLOT_OFFSET)
        party_data = c.read_memory(read_address, SLOT_DATA_SIZE)
        stats_data = c.read_memory(read_address + SLOT_DATA_SIZE + STAT_DATA_OFFSET, STAT_DATA_SIZE)
        if party_data and stats_data:
            data = party_data + stats_data
            try:
                pokemon = Pokemon6(data)
                party.append(pokemon)
            except ValueError:
                traceback.print_exc()
                pass
    return party

def print_bits(value):
    binary = bin(value)[2:].zfill(8)
    bits = [bool(int(bit)) for bit in binary]
    print(bits)

def analyze_statuses(self):
    print('begin statuses')
    # print('statuses:', self.statuses)
    print_bits(self.statusbyte)
    # Analyze bit positions
    print('Asleep:', self.asleep)
    print('Poisoned:', self.poisoned)
    print('Burned:', self.burned)
    print('Frozen:', self.frozen())
    print('Paralyzed:', self.paralyzed)
    # print('Toxic:', self.badlypoisoned())
    print('end statuses')

def calcPower(pkmn,move):
    if move in ('Eruption','Water Spout'):
        return int(int(pkmn.cur_hp)/int(pkmn.maxhp)*150)
    elif move['name']=='Return':
        return round(pkmn.friendship/2.5)
    elif move['name']=="Frustration":
        return round((255-pkmn.friendship)/2.5)
    elif move["name"] in ("Low Kick","Grass Knot"):
        return "WT"
    elif move['name']=="Fling":
        return "ITEM"
    elif move['name'] in ("Crush Grip","Wring Out"):
        return ">HP"
    elif move['name'] in ("Flail","Reversal"):
        if int(pkmn.cur_hp)/int(pkmn.maxhp)>=.6875:
            return 20
        elif int(pkmn.cur_hp)/int(pkmn.maxhp)>=.3542:
            return 40
        elif int(pkmn.cur_hp)/int(pkmn.maxhp)>=.2083:
            return 80
        elif int(pkmn.cur_hp)/int(pkmn.maxhp)>=.1042:
            return 100
        elif int(pkmn.cur_hp)/int(pkmn.maxhp)>=.0417:
            return 150
        elif int(pkmn.cur_hp)/int(pkmn.maxhp)<.0417:
            return 200
        else:
            return "ERR"
    else:
        return ('-' if not move['power'] else int(move['power']))
    
def movetype(pkmn,move,item):
    if move=="Revelation Dance":
        return (pkmn.types)[0]
    elif move=="Hidden Power":
        return "Null"
    elif move=="Natural Gift":
        return "Normal"
    elif move=="Judgement":
        if item=="298":
            return "Fire"
        elif item=="299":
            return "Water"
        elif item=="300":
            return "Electric"
        elif item=="301":
            return "Grass"
        elif item=="302":
            return "Ice"
        elif item=="303":
            return "Fighting"
        elif item=="304":
            return "Poison"
        elif item=="305":
            return "Ground"
        elif item=="306":
            return "Flying"
        elif item=="307":
            return "Psychic"
        elif item=="308":
            return "Bug"
        elif item=="309":
            return "Rock"
        elif item=="310":
            return "Ghost"
        elif item=="311":
            return "Dragon"
        elif item=="312":
            return "Dark"
        elif item=="313":
            return "Steel"
        elif item=="644":
            return "Fairy"
        else:
            return "Normal"
    elif move=="Techno Blast":
        if item=="116":
            return "Water"
        elif item=="117":
            return "Electric"
        elif item=="118":
            return "Fire"
        elif item=="119":
            return "Ice"
        else:
            return "Normal"
    elif move=="Multi-Attack":
        if item=="912":
            return "Fire"
        elif item=="913":
            return "Water"
        elif item=="915":
            return "Electric"
        elif item=="914":
            return "Grass"
        elif item=="917":
            return "Ice"
        elif item=="904":
            return "Fighting"
        elif item=="906":
            return "Poison"
        elif item=="907":
            return "Ground"
        elif item=="905":
            return "Flying"
        elif item=="916":
            return "Psychic"
        elif item=="909":
            return "Bug"
        elif item=="908":
            return "Rock"
        elif item=="910":
            return "Ghost"
        elif item=="918":
            return "Dragon"
        elif item=="919":
            return "Dark"
        elif item=="911":
            return "Steel"
        elif item=="920":
            return "Fairy"
        else:
            return "Normal"
    else:
        return move['type']
    
def getURLAbbr(game):
    if game == 15:
        return 'x-y'
    elif game == 16:
        return 'omega-ruby-alpha-sapphire/dex' ## ORAS sprites end in /dex
    else:
        return 'home'
    
def resize(image_file, new_size, encode_format='PNG'):
    im = Image.open(image_file)
    new_im = im.resize(new_size, Image.NEAREST)
    with BytesIO() as buffer:
        new_im.save(buffer, format=encode_format)
        data = buffer.getvalue()
    return data

def typeformatting(typing):
    typecolordict = {'Normal':'#999999', 'Fire':'#ff612c', 'Water':'#2892ff', 'Electric':'#ffdb00', 'Grass':'#42bf24', 
                  'Ice':'#42bfff', 'Fighting':'#ffa202', 'Poison':'#994dcf', 'Ground':'#ab7939', 'Flying':'#95c9ff',
                  'Psychic':'#ff637f', 'Bug':'#9fa523', 'Rock':'#bcb889', 'Ghost':'#6e4570', 'Dragon':'#7e44ed', 
                  'Dark':'#2f4f4f', 'Steel':'#708090', 'Fairy':'#ffb1ff'}
    typecolor = typecolordict[typing]
    return typecolor

def natureformatting(nl, s):
    naturedict = {'raised':'#f08080', 'lowered':'#87cefa', 'neutral':'#ffffff'}
    if nl[s] == 'raised':
        return naturedict['raised']
    elif nl[s] == 'lowered':
        return naturedict['lowered']
    else:
        return naturedict['neutral']

def statnotes(s, pos):
    nt = s['stats'][pos]
    if nt == ' ':
        s['stats'][pos] = '+'
    elif nt == '+':
        s['stats'][pos] = '-'
    elif nt == '-':
        s['stats'][pos] = '='
    elif nt == '=':
        s['stats'][pos] = ' '
    return s

def abil_popup(l):
    abilpopup = [
        [sg.Text('Abilities available:')],
        [sg.Combo(l, enable_events=True, key='-abilpopup-')],
        [sg.Button('Remove', key='-rem-'), sg.Button('Cancel')]
    ] 
    window = sg.Window('Ability Selector', abilpopup).Finalize()
    
    while True:
        event, values = window.read()

        if (event == sg.WINDOW_CLOSED) or (event == 'Cancel'):
            break
        elif event == '-rem-':
            break
        else:
            print('OVER')

    window.close()

    print('[GUI_POPUP] event:', event)
    print('[GUI_POPUP] values:', values)

    if values and values['-abilpopup-']:
        return values['-abilpopup-']

def run():
    try:
        #print('connecting to citra')
        c = Citra()
        #print('connected to citra')
        game=getGame(c)
        gamegroupid,gamegroupabbreviation,gen = cursor.execute(f"""
                select
                    gg.gamegroupid
                    ,gg.gamegroupabbreviation
                    ,gg.generationid
                from "pokemon.gamegroup" gg
                where gamegroupname = '{game}'""").fetchone()
        print('running..')
        
        ### SET UP TRACKER GUI ###
        topcol1 = [
            [sg.Combo([], visible=False, font=('Franklin Gothic Medium', 14), enable_events=True, key='-slotdrop-', readonly=True, expand_x=True, background_color='black', text_color='white')],
            [sg.Text('Loading...', key='-slot-'),],
            [sg.Image(key='-monimg-')], 
            [sg.Text(justification='c', key='-monname-'), sg.Text(font=('Arial', 11, 'bold'), key='-monnum-')],
            [sg.Image(key='-typeimg1-'), sg.Text(key='-typename1-'), sg.Image(key='-typeimg2-', visible=False), sg.Text(key='-typename2-', visible=False), sg.Image(key='-typeimg3-', visible=False), sg.Text(key='-typename3-', visible=False),],
            [sg.Text(key='-level-'), sg.Text(key='-evo-', visible = False), sg.Image(key='-status-', visible = False)],
            [sg.Text(key='-ability-')],
            [sg.Text(key='-item-')],
        ]
        topcol2 = [
            [sg.Text('HP:', key='-hplabel-', visible=False)],
            [sg.Text('Atk:', key='-attlabel-', visible=False)],
            [sg.Text('Def:', key='-deflabel-', visible=False)],
            [sg.Text('SpAtk:', key='-spattlabel-', visible=False)],
            [sg.Text('SpDef:', key='-spdeflabel-', visible=False)],
            [sg.Text('Speed:', key='-speedlabel-', visible=False)],
            [sg.Text('BST:', key='-bstlabel-', visible=False)],
        ]
        topcol3 = [
            [sg.Text(key='-hp-', justification='r')],
            [sg.Image(key='-attmod-'), sg.Text(key='-att-', justification='r')],
            [sg.Image(key='-defmod-'), sg.Text(key='-def-', justification='r')],
            [sg.Image(key='-spattmod-'), sg.Text(key='-spatt-', justification='r')],
            [sg.Image(key='-spdefmod-'), sg.Text(key='-spdef-', justification='r')],
            [sg.Image(key='-speedmod-'), sg.Text(key='-speed-', justification='r')],
            [sg.Text(key='-bst-', justification='r')],
        ]

        botcol1 = [
            [sg.Text(key='-movehdr-', justification='l')],
            [sg.Image(key='-mv1type-'), sg.Text(key='-mv1text-')],
            [sg.Image(key='-mv2type-'), sg.Text(key='-mv2text-')],
            [sg.Image(key='-mv3type-'), sg.Text(key='-mv3text-')],
            [sg.Image(key='-mv4type-'), sg.Text(key='-mv4text-')],
        ]
        botcol2 = [
            [sg.Text(key='-movepphdr-', size=5, justification='c')],
            [sg.Text(key='-mv1pp-', size=5, justification='r'), sg.Image(key='-mv1mod-'),],
            [sg.Text(key='-mv2pp-', size=5, justification='r'), sg.Image(key='-mv2mod-'),],
            [sg.Text(key='-mv3pp-', size=5, justification='r'), sg.Image(key='-mv3mod-'),],
            [sg.Text(key='-mv4pp-', size=5, justification='r'), sg.Image(key='-mv4mod-'),],
        ]
        # botcol3 = [
        #     [sg.Image(key='-mvmodhdr-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv1mod-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv2mod-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv3mod-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv4mod-'), sg.Text(size=(0,1))],
        # ]
        botcol4 = [
            [sg.Text(key='-movebphdr-', size=3, justification='r')],
            [sg.Text(key='-mv1bp-', size=3, justification='r')],
            [sg.Text(key='-mv2bp-', size=3, justification='r')],
            [sg.Text(key='-mv3bp-', size=3, justification='r')],
            [sg.Text(key='-mv4bp-', size=3, justification='r')],
        ]
        botcol5 = [
            [sg.Text(key='-moveacchdr-', size=3, justification='c')],
            [sg.Text(key='-mv1acc-', size=3, justification='c')],
            [sg.Text(key='-mv2acc-', size=3, justification='c')],
            [sg.Text(key='-mv3acc-', size=3, justification='c')],
            [sg.Text(key='-mv4acc-', size=3, justification='c')],
        ]
        botcol6 = [
            [sg.Text(key='-movecontacthdr-', size=1, justification='c')],
            [sg.Text(key='-mv1ctc-', size=1, justification='c')],
            [sg.Text(key='-mv2ctc-', size=1, justification='c')],
            [sg.Text(key='-mv3ctc-', size=1, justification='c')],
            [sg.Text(key='-mv4ctc-', size=1, justification='c')],
        ]

        topcol1a = [
            [sg.Text(key='-slot-e-'),],
            [sg.Image(key='-monimg-e-')], 
            [sg.Text(justification='c', key='-monname-e-'), sg.Text(font=('Arial', 11, 'bold'), key='-monnum-e-')],
            [sg.Image(key='-typeimg1-e-'), sg.Text(key='-typename1-e-'), sg.Image(key='-typeimg2-e-', visible=False), sg.Text(key='-typename2-e-', visible=False),],
            [sg.Text(key='-level-e-'), sg.Text(key='-evo-e-', visible = False), sg.Image(key='-status-e-', visible = False)],
            [sg.Text(key='-ability-e-')],
            [sg.Text(key='-note-e-')],
        ]
        topcol2a = [
            [sg.Text('HP:', key='-hplabel-e-')],
            [sg.Text('Atk:', key='-attlabel-e-')],
            [sg.Text('Def:', key='-deflabel-e-')],
            [sg.Text('SpAtk:', key='-spattlabel-e-')],
            [sg.Text('SpDef:', key='-spdeflabel-e-')],
            [sg.Text('Speed:', key='-speedlabel-e-')],
            [sg.Text('BST:', key='-bstlabel-e-')],
            # [sg.Text('Add abil', key='-addabil-e-', justification='l')], 
            # [sg.Text('Rem abil', key='-remabil-e-', justification='l')],
            # [sg.Text('Add note', key='-addnote-e-', justification='l')],
            [sg.Button('+ Ability', key='-addabil-e-', font=('Franklin Gothic Medium', 12), auto_size_button=True)], 
            [sg.Button('Add Note', key='-addnote-e-', font=('Franklin Gothic Medium', 12), auto_size_button=True)],
        ]
        topcol3a = [
            [sg.Text('[ ]', key='-hp-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Image(key='-attmod-e-'), sg.Text('[ ]', key='-att-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Image(key='-defmod-e-'), sg.Text('[ ]', key='-def-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Image(key='-spattmod-e-'), sg.Text('[ ]', key='-spatt-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Image(key='-spdefmod-e-'), sg.Text('[ ]', key='-spdef-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Image(key='-speedmod-e-'), sg.Text('[ ]', key='-speed-e-', enable_events=True, font=('Consolas', 17))],
            [sg.Text(key='-bst-e-')],
            [sg.Button('- Ability', key='-remabil-e-', font=('Franklin Gothic Medium', 12), auto_size_button=True)],
            [sg.Text('')], 
        ]

        botcol1a = [
            [sg.Text(key='-movehdr-e-', justification='l')],
            [sg.Image(key='-mv1type-e-'), sg.Text(key='-mv1text-e-')],
            [sg.Image(key='-mv2type-e-'), sg.Text(key='-mv2text-e-')],
            [sg.Image(key='-mv3type-e-'), sg.Text(key='-mv3text-e-')],
            [sg.Image(key='-mv4type-e-'), sg.Text(key='-mv4text-e-')],
        ]
        botcol2a = [
            [sg.Text('PP', key='-movepphdr-e-', size=5, justification='c')],
            [sg.Text(key='-mv1pp-e-', size=5, justification='r'), sg.Image(key='-mv1mod-e-'),],
            [sg.Text(key='-mv2pp-e-', size=5, justification='r'), sg.Image(key='-mv2mod-e-'),],
            [sg.Text(key='-mv3pp-e-', size=5, justification='r'), sg.Image(key='-mv3mod-e-'),],
            [sg.Text(key='-mv4pp-e-', size=5, justification='r'), sg.Image(key='-mv4mod-e-'),],
        ]
        # botcol3a = [
        #     [sg.Image(key='-mvmodhdr-e-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv1mod-e-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv2mod-e-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv3mod-e-'), sg.Text(size=(0,1))],
        #     [sg.Image(key='-mv4mod-e-'), sg.Text(size=(0,1))],
        # ]
        botcol4a = [
            [sg.Text('BP', key='-movebphdr-e-', size=3, justification='r')],
            [sg.Text(key='-mv1bp-e-', size=3, justification='r')],
            [sg.Text(key='-mv2bp-e-', size=3, justification='r')],
            [sg.Text(key='-mv3bp-e-', size=3, justification='r')],
            [sg.Text(key='-mv4bp-e-', size=3, justification='r')],
        ]
        botcol5a = [
            [sg.Text('Acc', key='-moveacchdr-e-', size=3, justification='c')],
            [sg.Text(key='-mv1acc-e-', size=3, justification='c')],
            [sg.Text(key='-mv2acc-e-', size=3, justification='c')],
            [sg.Text(key='-mv3acc-e-', size=3, justification='c')],
            [sg.Text(key='-mv4acc-e-', size=3, justification='c')],
        ]
        botcol6a = [
            [sg.Text('C', key='-movecontacthdr-e-', size=1, justification='c')],
            [sg.Text(key='-mv1ctc-e-', size=1, justification='c')],
            [sg.Text(key='-mv2ctc-e-', size=1, justification='c')],
            [sg.Text(key='-mv3ctc-e-', size=1, justification='c')],
            [sg.Text(key='-mv4ctc-e-', size=1, justification='c')],
        ]
        botcol7a = [
            [sg.Text(key='-abillist-e-', justification='l', font=('Franklin Gothic Medium', 12))],
            [sg.Text(key='-prevmoves-e-', justification='l', font=('Franklin Gothic Medium', 12), size=(50, 3))],
            # [sg.Text(key='-mv4ctc-e-', size=1, justification='c')],
        ]

        layout = [[
            sg.Column([[
                sg.Column(topcol1, key='-TLCOL1-', size=(250, 380)), 
                sg.Column(topcol2, key='-TLCOL2-'), 
                sg.Column(topcol3, element_justification='right', key='-TLCOL3-')
            ], 
            [
                sg.Column(botcol1), 
                sg.Column(botcol2), 
                # sg.Column(botcol3), 
                sg.Column(botcol4), 
                sg.Column(botcol5),
                sg.Column(botcol6),
            ]], size=(450, 700)), 
            sg.VerticalSeparator(key='-vs-'),
            sg.Column([[
                sg.Column(topcol1a, size=(250, 380), key='-tc1a-e-', visible = False), 
                sg.Column(topcol2a, size=(80, 350), key='-tc2a-e-', visible = False), 
                sg.Column(topcol3a, size=(80, 350), element_justification='right', key='-tc3a-e-', visible = False)
            ], 
            [
                sg.Column(botcol1a, key='-bc1a-e-', visible = False), 
                sg.Column(botcol2a, element_justification='right', key='-bc2a-e-', visible = False), 
                # sg.Column(botcol3a, element_justification='right', key='-bc3a-e-', visible = False), 
                sg.Column(botcol4a, element_justification='right', key='-bc4a-e-', visible = False), 
                sg.Column(botcol5a, element_justification='right', key='-bc5a-e-', visible = False), 
                sg.Column(botcol6a, element_justification='right', key='-bc6a-e-', visible = False)
            ], 
            [
                sg.Column(botcol7a, key='-bc7a-e-', visible = False), 
            ]], size=(450, 700))
        ]]
        window = sg.Window(track_title, layout, track_size, background_color='black', resizable=True)
        loops = 0
        slotchoice = ''
        enemymon = ''
        enemydict = {"abilities": [], "stats": ["", "", "", "", "", ""], "notes": "", "levels": [], "moves": []}
        while (True):
            try:
                if c.is_connected():
                    if loops == 0:
                        trackdata=json.load(open(trackadd,"r+"))
                    event, values = window.Read(timeout=8000)
                    if event == sg.WIN_CLOSED:
                        break
                    elif event == '-slotdrop-':
                        slotchoice = values['-slotdrop-']
                        window['-slotdrop-'].widget.select_clear()
                    elif event == '-hp-e-':
                        u = statnotes(enemydict, 0)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-hp-e-'].update('[{}]'.format(u['stats'][0]))
                    elif event == '-att-e-':
                        u = statnotes(enemydict, 1)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-att-e-'].update('[{}]'.format(u['stats'][1]))
                    elif event == '-def-e-':
                        u = statnotes(enemydict, 2)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-def-e-'].update('[{}]'.format(u['stats'][2]))
                    elif event == '-spatt-e-':
                        u = statnotes(enemydict, 3)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-spatt-e-'].update('[{}]'.format(u['stats'][3]))
                    elif event == '-spdef-e-':
                        u = statnotes(enemydict, 4)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-spdef-e-'].update('[{}]'.format(u['stats'][4]))
                    elif event == '-speed-e-':
                        u = statnotes(enemydict, 5)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-speed-e-'].update('[{}]'.format(u['stats'][5]))
                    elif event == '-addnote-e-':
                        note = sg.popup_get_text('Enter note:', title='Note', default_text=enemydict['notes'])
                        trackdata[enemymon]['notes'] = note
                        window['-note-e-'].update(trackdata[enemymon]['notes'])
                    elif event == '-addabil-e-':
                        abil = sg.popup_get_text('Enter ability:', title='Ability')
                        trackdata[enemymon]['abilities'].append(abil)
                        window['-abillist-e-'].update(trackdata[enemymon]['abilities'])
                    elif event == '-remabil-e-':
                        remabil = abil_popup(enemydict['abilities'])
                        trackdata[enemymon]['abilities'].remove(remabil)
                        window['-abillist-e-'].update(trackdata[enemymon]['abilities'])
                    partyadd,enemyadd,ppadd,curoppnum,enctype,mongap=getaddresses(c)
                    # print("loops" + str(loops))
                    loops+=1
                    #print('reading party')
                    party1=read_party(c,partyadd)
                    party2=read_party(c,enemyadd)
                    party=party1+party2
                    pk=1
                    #print('read party... performing loop')
                    #skips trainer mons that arent out yet
                    enemynum=int.from_bytes(c.read_memory(curoppnum,2),"little")
                    pkmni=0
                    emon = ''
                    for pkmn in party:
                        if pkmn in party1:
                            if pkmn.species_num()==0:
                                party1.remove(pkmn)
                    for pkmn in party2:
                        pkmni+=1
                        if pkmn.species_num()!=enemynum:
                            party.remove(pkmn)
                        else:
                            pkmnindex=(pkmni)
                            break
                    typelist=["Normal","Fighting","Flying","Poison","Ground","Rock","Bug","Ghost","Steel","Fire","Water","Grass","Electric","Psychic","Ice","Dragon","Dark","Fairy"]
                    enemytypes=[]
                    try:
                        if gen==6:
                            pke=pkmnindex+len(party1)
                        elif gen==7:
                            pke=pkmnindex+12
                        typereadere=c.read_memory(ppadd+(mongap*(pke-1))-(2*(gen+6)),2) #(2*(gen+6))
                        for byte in typereadere:
                            if typelist[byte] not in enemytypes:
                                enemytypes.append(typelist[byte])
                    except Exception:
                        print(Exception)
                    slot = []
                    for pkmn in party:
                        if pkmn.species_num() in range (1,808): ### Make sure the slot is valid & not an egg
                            pkmn.getAtts(gamegroupid,gen)
                            if int(pkmn.cur_hp) > 5000: ### Make sure the memory dump hasn't happened (or whatever causes the invalid values)
                                continue
                            if pkmn in party2:
                                if gen==6:
                                    pk=pkmnindex+len(party1)
                                elif gen==7:
                                    pk=pkmnindex+12
                            else:
                                slot.append(pkmn.name)
                            if (slotchoice == ''):
                                slotchoice = pkmn.name # only kicks the first time through the code
                                antici = 0
                            # if (slotchoice not in slot):
                            #     slotchoice = pkmn.name
                            #     antici = 0
                            #     print('updated for new party config')
                            # print(slot)
                            window['-slotdrop-'].Update(values=slot, value=slotchoice, visible=True)
                            print(enctype, ';;;', pkmn.name, ';;;', party.index(pkmn)+1, ';;;',)
                            if enctype!='p':
                                #grabs in battle types
                                pkmntypes=[]
                                currmon = pkmn
                                typereader=c.read_memory(ppadd+(mongap*(pk-1))-(2*(gen+6)),2)
                                for byte in typereader: # this triggers a list index out of range error in multis
                                    if typelist[byte] not in pkmntypes:
                                        pkmntypes.append(typelist[byte])
                                # print('unknown flags')
                                # print_bits(pkmn.alt_form)
                                # print_bits(pkmn.unknown_flags_ea())
                                # print_bits(pkmn.unknown_flags_eb())
                                # analyze_statuses(pkmn)
                                #### Begin Pokemon div
                                if (pkmn in party1) and (pkmn.name == slotchoice): 
                                    currmon = pkmn
                                    for type in pkmn.types:
                                        window['-typeimg{}-'.format(pkmn.types.index(type) + 1)].Update(resize('images/types/{}.png'.format(type[0]), (27, 24)), visible = True)
                                        window['-typename{}-'.format(pkmn.types.index(type) + 1)].Update('{}'.format(type[0]), text_color=typeformatting(type[0]), visible = True)
                                        if len(pkmn.types) < 2:
                                            window['-typeimg2-'].Update(visible = False)
                                            window['-typename2-'].Update(visible = False)
                                            window['-typeimg3-'].Update(visible = False)
                                            window['-typename3-'].Update(visible = False)
                                        elif len(pkmn.types) < 3:
                                            window['-typeimg3-'].Update(visible = False)
                                            window['-typename3-'].Update(visible = False)
                                    if pkmn.evo:
                                        if pkmn.name == 'Eevee':
                                            evoitem = 'Any stone'
                                        elif pkmn.name == 'Gloom':
                                            evoitem = 'Leaf Stone/Sun Stone'
                                        elif pkmn.name == 'Poliwhirl':
                                            evoitem = 'Water Stone/Kings Rock'
                                        elif pkmn.name == 'Clamperl':
                                            evoitem = 'Deep Sea Tooth/Deep Sea Scale'
                                        # need to check slowpoke, kirlia, snorunt
                                        else:
                                            evoitem = ('' if not pkmn.evoitem else 'w/'+pkmn.evoitem)
                                            evofriend = ('' if pkmn.evotype != 'Friendship' else 'w/ high friendship')
                                            evolevel = ('' if not pkmn.evolevel else '@ level '+str(int(pkmn.evolevel)))
                                            evostring = ('' if not pkmn.evostring else pkmn.evostring)
                                            evoloc = ('' if not pkmn.evolocation else 'in '+pkmn.evolocation)
                                        window['-evo-'].update('>', visible = True)
                                        window['-evo-'].set_tooltip('Evolves {}{}{}{}{}'.format(evoitem, evofriend, evolevel, evostring, evoloc))
                                    else:
                                        window['-evo-'].update(visible = False)
                                    if gen==6:
                                        levelnum=int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))-256,1))
                                        batabilnum=int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))+6-264),1))
                                        hpnum=[int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-264),2),"little"),int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-266),2),"little")]
                                    elif gen==7:
                                        levelnum=int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))-486,1))
                                        batabilnum=int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))+0x36),1))
                                        hpnum=[int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-494),2),"little"),int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-496),2),"little")]
                                    if pkmn.status != '':
                                        window['-status-'].Update(resize('images/statuses/{}.png'.format(pkmn.status), (75, 20)), visible = True)
                                    else:
                                        window['-status-'].Update(visible = False)
                                    query=f"""select
                                            ab.abilityname
                                            ,abilitydescription
                                        from "pokemon.generationability" ga
                                            left join "pokemon.ability" ab on ga.abilityid = ab.abilityid
                                            left join "pokemon.abilitylookup" al on ab.abilityname = al.abilityname
                                        where al.abilityindex = {batabilnum} and ga.generationid <= {gen} 
                                        order by ga.generationid desc
                                        """ 
                                    abilityname,abilitydescription = cursor.execute(query).fetchone()
                                    ### STATS ########
                                    #print(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-264),1)))
                                    attackchange,defchange,spatkchange,spdefchange,speedchange = pkmn.getStatChanges()
                                    naturelist = [attackchange,defchange,spatkchange,spdefchange,speedchange]
                                    ### MOVES ########
                                    totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    if pkmn.held_item_name == pkmn.held_item_name:
                                        frisk = 1
                                    else:  
                                        frisk = 0
                                    query=f"""select
                                            itemname
                                            ,itemdesc
                                        from "generationitem" 
                                        where itemname = '{pkmn.held_item_name}' and genid <= {gen}
                                        """
                                    itemname,itemdesc = cursor.execute(query).fetchone()
                                    window['-slot-'].Update('Slot {} - {}'.format(str(party.index(pkmn)+1), 'Battle'))
                                    try:
                                        window['-monimg-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                    except:
                                        window['-monimg-'].Update(visible = False)
                                        print(Exception)
                                    window['-monname-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                    window['-monnum-'].Update('#{}'.format(str(pkmn.species_num())))
                                    window['-level-'].Update('Level: {}'.format(levelnum))
                                    window['-level-'].set_tooltip('Seen at {}'.format(trackdata[pkmn.name]["levels"]))
                                    window['-ability-'].Update(str(pkmn.ability['name']))
                                    window['-ability-'].set_tooltip(str(pkmn.ability['description']))
                                    window['-item-'].Update(pkmn.held_item_name)
                                    window['-item-'].set_tooltip(itemdesc)
                                    window['-hplabel-'].Update(visible = True)
                                    window['-attlabel-'].update(visible = True, text_color=natureformatting(naturelist, 0))
                                    window['-deflabel-'].update(visible = True, text_color=natureformatting(naturelist, 1))
                                    window['-spattlabel-'].update(visible = True, text_color=natureformatting(naturelist, 2))
                                    window['-spdeflabel-'].update(visible = True, text_color=natureformatting(naturelist, 3))
                                    window['-speedlabel-'].update(visible = True, text_color=natureformatting(naturelist, 4))
                                    window['-bstlabel-'].Update(visible = True)
                                    window['-hp-'].Update('{}/{}'.format(hpnum[0], hpnum[1]))
                                    window['-hp-'].set_tooltip('EV: ' + str(pkmn.evhp))
                                    window['-att-'].Update(pkmn.attack, text_color=natureformatting(naturelist, 0))
                                    window['-att-'].set_tooltip('EV: ' + str(pkmn.evattack))
                                    window['-def-'].Update(pkmn.defense, text_color=natureformatting(naturelist, 1))
                                    window['-def-'].set_tooltip('EV: ' + str(pkmn.evdefense))
                                    window['-spatt-'].Update(pkmn.spatk, text_color=natureformatting(naturelist, 2))
                                    window['-spatt-'].set_tooltip('EV: ' + str(pkmn.evspatk))
                                    window['-spdef-'].Update(pkmn.spdef, text_color=natureformatting(naturelist, 3))
                                    window['-spdef-'].set_tooltip('EV: ' + str(pkmn.evspdef))
                                    window['-speed-'].Update(pkmn.speed, text_color=natureformatting(naturelist, 4))
                                    window['-speed-'].set_tooltip('EV: ' + str(pkmn.evspeed))
                                    window['-attmod-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-20),1))), visible = True)
                                    window['-defmod-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-19),1))), visible = True)
                                    window['-spattmod-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-18),1))), visible = True)
                                    window['-spdefmod-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-17),1))), visible = True)
                                    window['-speedmod-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-16),1))), visible = True)
                                    window['-bst-'].Update(pkmn.bst)
                                    window['-movehdr-'].update('Moves {}/{} ({})'.format(learnedcount, totallearn, nmove))
                                    window['-movehdr-'].set_tooltip(learnstr)
                                    window['-movepphdr-'].update('PP')
                                    window['-movebphdr-'].update('BP')
                                    window['-moveacchdr-'].update('Acc')
                                    window['-movecontacthdr-'].update('C')
                                    for move in pkmn.moves:
                                        stab = ''
                                        movetyp=movetype(pkmn,move,pkmn.held_item_num)
                                        for type in pkmn.types:
                                            if move['type'] == type[0]:
                                                stab = move['type']
                                                continue
                                        typetable={
                                            "Normal":[1,1,1,1,1,.5,1,0,.5,1,1,1,1,1,1,1,1,1,1],
                                            "Fighting":[2,1,.5,.5,1,2,.5,0,2,1,1,1,1,.5,2,1,2,.5,1],
                                            "Flying":[1,2,1,1,1,.5,2,1,.5,1,1,2,.5,1,1,1,1,1,1],
                                            "Poison":[1,1,1,.5,.5,.5,1,.5,0,1,1,2,1,1,1,1,1,2,1],
                                            "Ground":[1,1,0,2,1,2,.5,1,2,2,1,.5,2,1,1,1,1,1,1],
                                            "Rock":[1,.5,2,1,.5,1,2,1,.5,2,1,1,1,1,2,1,1,1,1],
                                            "Bug":[1,.5,.5,.5,1,1,1,.5,.5,.5,1,2,1,2,1,1,2,.5,1],
                                            "Ghost":[0,1,1,1,1,1,1,2,1,1,1,1,1,2,1,1,.5,1,1],
                                            "Steel":[1,1,1,1,1,2,1,1,.5,.5,.5,1,.5,1,2,1,1,2,1],
                                            "Fire":[1,1,1,1,1,.5,2,1,2,.5,.5,2,1,1,2,.5,1,1,1],
                                            "Water":[1,1,1,1,2,2,1,1,1,2,.5,.5,1,1,1,.5,1,1,1],
                                            "Grass":[1,1,.5,.5,2,2,.5,1,.5,.5,2,.5,1,1,1,.5,1,1,1],
                                            "Electric":[1,1,2,1,0,1,1,1,1,1,2,.5,.5,1,1,.5,1,1,1],
                                            "Psychic":[1,2,1,2,1,1,1,1,.5,1,1,1,1,.5,1,1,0,1,1],
                                            "Ice":[1,1,2,1,2,1,1,1,.5,.5,.5,2,1,1,.5,2,1,1,1],
                                            "Dragon":[1,1,1,1,1,1,1,1,.5,1,1,1,1,1,1,2,1,0,1],
                                            "Dark":[1,.5,1,1,1,1,1,2,1,1,1,1,1,2,1,1,.5,.5,1],
                                            "Fairy":[1,2,1,.5,1,1,1,1,.5,.5,1,1,1,1,1,2,2,1,1],
                                            "Null":[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
                                            "-":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                                        }
                                        #defines the columns for the arrays corresponding to the type hit
                                        typedic={"Normal":0,"Fighting":1,"Flying":2,"Poison":3,"Ground":4,"Rock":5,"Bug":6,"Ghost":7,"Steel":8,"Fire":9,"Water":10,"Grass":11,"Electric":12,"Psychic":13,"Ice":14,"Dragon":15,"Dark":16,"Fairy":17,"Null":18}
                                        typemult=1
                                        if movetyp!=None:
                                            for type in enemytypes:
                                                typemult=typemult*(typetable[movetyp][typedic[type]])
                                        if move["category"]!="Non-Damaging":
                                            if typemult==.25:
                                                modimage="4"
                                            elif typemult==.5:
                                                modimage="5"
                                            elif typemult==1:
                                                modimage="6"
                                            elif typemult==2:
                                                modimage="7"
                                                antici = 1
                                            elif typemult==4:
                                                modimage="8"
                                                antici = 1
                                            elif typemult==0:
                                                modimage="X"
                                        else:
                                            modimage="6"
                                        movepower = calcPower(pkmn,move)
                                        acc = '-' if not move['acc'] else int(move['acc'])
                                        contact = ('Y' if move['contact'] else 'N')
                                        window['-mv{}type-'.format(pkmn.moves.index(move) + 1)].update(resize('images/categories/{}.png'.format(move["category"]), (27,20)))
                                        window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].update(move["name"], text_color=typeformatting(move['type']))
                                        window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].set_tooltip(move["description"])
                                        window['-mv{}pp-'.format(pkmn.moves.index(move) + 1)].update('{}/{}'.format(int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1)), int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+1+(14*(pkmn.moves).index(move)),1))))
                                        window['-mv{}mod-'.format(pkmn.moves.index(move) + 1)].update('images/modifiers/modifier{}.png'.format(modimage))
                                        if stab == move['type']:
                                            window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(movepower, text_color=typeformatting(move['type']))
                                        else:
                                            window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(movepower, text_color='white')
                                        window['-mv{}acc-'.format(pkmn.moves.index(move) + 1)].update(acc)
                                        window['-mv{}ctc-'.format(pkmn.moves.index(move) + 1)].update(contact)
                                # elif (pkmn in party2) & (party.index(pkmn)+1):
                                elif (pkmn in party2) & ((party.index(pkmn)+1 == 7) | (party.index(pkmn)+1 == 1)): # this works for singles in XY, needs testing for all other games; only access first mon stuff, may want to figure out a way to include double battle (may not work for multis)
                                    # print(pkmn.name, ';;;', pkmn.species, ';;;', party.index(pkmn)+1)
                                    if (emon != pkmn) & (emon == emon): # washing the data on mon change (the stat mods may not be needed, but keeping here for now)
                                        ct = 0
                                        enemymon = pkmn.name
                                        enemydict = trackdata[pkmn.name]
                                        while ct < 4:
                                            ct += 1
                                            window['-mv{}type-e-'.format(ct)].update(visible = False)
                                            window['-mv{}text-e-'.format(ct)].update(visible = False)
                                            window['-mv{}pp-e-'.format(ct)].update(visible = False)
                                            window['-mv{}mod-e-'.format(ct)].update(visible = False)
                                            window['-mv{}bp-e-'.format(ct)].update(visible = False)
                                            window['-mv{}acc-e-'.format(ct)].update(visible = False)
                                            window['-mv{}ctc-e-'.format(ct)].update(visible = False)
                                    for type in pkmn.types:
                                        window['-typeimg{}-e-'.format(pkmn.types.index(type) + 1)].Update(resize('images/types/{}.png'.format(type[0]), (27, 24)), visible = True)
                                        window['-typename{}-e-'.format(pkmn.types.index(type) + 1)].Update('{}'.format(type[0]), text_color=typeformatting(type[0]), visible = True)
                                        if len(pkmn.types) == 1:
                                            window['-typeimg2-e-'].Update(visible = False)
                                            window['-typename2-e-'].Update(visible = False)
                                    if pkmn.evo:
                                        # evotype = ('' if not pkmn.evotype else pkmn.evotype)
                                        evoitem = ('' if not pkmn.evoitem else 'w/'+pkmn.evoitem)
                                        evofriend = ('' if pkmn.evotype != 'Friendship' else 'w/ high friendship')
                                        evolevel = ('' if not pkmn.evolevel else '@ level '+str(int(pkmn.evolevel)))
                                        evostring = ('' if not pkmn.evostring else pkmn.evostring)
                                        evoloc = ('' if not pkmn.evolocation else 'in '+pkmn.evolocation)
                                        window['-evo-e-'].update('>', visible = True)
                                        window['-evo-e-'].set_tooltip('Evolves {}{}{}{}{}'.format(evoitem, evofriend, evolevel, evostring, evoloc))
                                    else:
                                        window['-evo-e-'].update(visible = False)
                                    if gen==6:
                                        levelnum=int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))-256,1))
                                        batabilnum=int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))+6-264),1))
                                        hpnum=[int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-264),2),"little"),int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-266),2),"little")]
                                    elif gen==7:
                                        levelnum=int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))-486,1))
                                        batabilnum=int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))+0x36),1))
                                        hpnum=[int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-494),2),"little"),int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-496),2),"little")]
                                    if pkmn.status != '':
                                        window['-status-e-'].Update(resize('images/statuses/{}.png'.format(pkmn.status), (75, 20)), visible = True)
                                    else:
                                        window['-status-e-'].Update(visible = False)
                                    query=f"""select
                                            ab.abilityname
                                            ,abilitydescription
                                        from "pokemon.generationability" ga
                                            left join "pokemon.ability" ab on ga.abilityid = ab.abilityid
                                            left join "pokemon.abilitylookup" al on ab.abilityname = al.abilityname
                                        where al.abilityindex = {batabilnum} and ga.generationid <= {gen}
                                        order by ga.generationid desc
                                        """
                                    totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                    abilityname,abilitydescription = cursor.execute(query).fetchone()
                                    startupabils=["Air Lock","Cloud Nine","Delta Stream","Desolate Land","Download","Drizzle","Drought","Forewarn","Imposter","Intimidate","Mold Breaker","Pressure","Primordial Sea","Sand Stream","Slow Start","Snow Warning","Teravolt","Turboblaze","Trace","Unnerve","Aura Break","Fairy Aura","Dark Aura",]
                                    if frisk == 1:
                                        startupabils.append('Frisk')
                                    if antici == 1:
                                        startupabils.append('Anticipation')
                                    if abilityname in startupabils:
                                        window['-ability-e-'].Update(str(pkmn.ability['name']))
                                        window['-ability-e-'].set_tooltip(str(pkmn.ability['description']))
                                        if pkmn.abilityname not in trackdata[pkmn.name]['abilities']:
                                            trackdata[pkmn.name]['abilities'].append(pkmn.abilityname)
                                    else:
                                        window['-ability-e-'].Update('Unknown Ability')
                                    if pkmn.level not in trackdata[pkmn.name]['levels']:
                                        trackdata[pkmn.name]['levels'].append(pkmn.level)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    # show enemy stuff in battle
                                    window['-tc1a-e-'].Update(visible = True)
                                    window['-tc2a-e-'].Update(visible = True)
                                    window['-tc3a-e-'].Update(visible = True)
                                    window['-bc1a-e-'].Update(visible = True)
                                    window['-bc2a-e-'].Update(visible = True)
                                    # window['-bc3a-e-'].Update(visible = False)
                                    window['-bc4a-e-'].Update(visible = True)
                                    window['-bc5a-e-'].Update(visible = True)
                                    window['-bc6a-e-'].Update(visible = True)
                                    window['-bc7a-e-'].Update(visible = True)
                                    # update enemy slot info
                                    window['-slot-e-'].Update('Slot {} - {}'.format(str(party.index(pkmn)+1), 'Battle'))
                                    try:
                                        window['-monimg-e-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                    except:
                                        window['-monimg-e-'].Update(visible = False)
                                        print(Exception)
                                    window['-monname-e-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                    window['-monnum-e-'].Update('#{}'.format(str(pkmn.species_num())))
                                    window['-level-e-'].Update('Level: {}'.format(levelnum))
                                    window['-level-e-'].set_tooltip('Seen at {}'.format(trackdata[pkmn.name]["levels"]))
                                    window['-note-e-'].update(trackdata[pkmn.name]["notes"])
                                    window['-note-e-'].set_tooltip(trackdata[pkmn.name]["notes"])
                                    window['-hp-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][0]))
                                    window['-att-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][1]))
                                    window['-def-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][2]))
                                    window['-spatt-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][3]))
                                    window['-spdef-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][4]))
                                    window['-speed-e-'].update('[{}]'.format(trackdata[pkmn.name]['stats'][5]))
                                    window['-bst-e-'].Update(pkmn.bst)
                                    window['-attmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-20),1))), visible = True)
                                    window['-defmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-19),1))), visible = True)
                                    window['-spattmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-18),1))), visible = True)
                                    window['-spdefmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-17),1))), visible = True)
                                    window['-speedmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-16),1))), visible = True)
                                    window['-movehdr-e-'].update('Moves {}/{} ({})'.format(learnedcount, totallearn, nmove))
                                    window['-movehdr-e-'].set_tooltip(learnstr)
                                    window['-movepphdr-e-'].update('PP')
                                    window['-movebphdr-e-'].update('BP')
                                    window['-moveacchdr-e-'].update('Acc')
                                    window['-movecontacthdr-e-'].update('C')
                                    window['-prevmoves-e-'].update('Previous Moves: ' + re.sub('[^A-Za-z0-9 ]+', '', str(trackdata[pkmn.name]['moves'])))
                                    window['-abillist-e-'].update('Known Abilities: ' + re.sub('[^A-Za-z0-9 ]+', '', str(trackdata[pkmn.name]['abilities'])))
                                    ### STATS ########
                                    ### MOVES ########
                                    totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                    # counts = pkmn.getCoverage(gen,gamegroupid)
                                    # countstr = ''
                                    # for dmg,count in counts:
                                    #     countstr+='<div class="damage-bracket">['+str(dmg)+'x]</div>'
                                    #     countstr+='<div class="bracket-count">'+str(count)+'</div>'
                                    if pkmn.level not in trackdata[pkmn.name]['levels']:
                                        trackdata[pkmn.name]['levels'].append(pkmn.level)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    movect = 0
                                    for move in pkmn.moves:
                                        if int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1))==int.from_bytes(c.read_memory(ppadd+1+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1)): 
                                            continue
                                        # if movetyp!=None:
                                        #     for type in currmon.types:
                                        #         typemult=typemult*(typetable[movetyp][typedic[type]])
                                        # if move["category"]!="Non-Damaging":
                                        #     if typemult==.25:
                                        #         modimage="4"
                                        #     elif typemult==.5:
                                        #         modimage="5"
                                        #     elif typemult==1:
                                        #         modimage="6"
                                        #     elif typemult==2:
                                        #         modimage="7"
                                        #     elif typemult==4:
                                        #         modimage="8"
                                        #     elif typemult==0:
                                        #         modimage="X"
                                        # else:
                                        #     modimage="6"
                                        stab = ''
                                        for type in pkmn.types:
                                            if move['type'] == type[0]:
                                                stab = move['type']
                                                continue
                                        movepower = calcPower(pkmn,move)
                                        acc = '-' if not move['acc'] else int(move['acc'])
                                        contact = ('Y' if move['contact'] else 'N')
                                        if move['name'] not in trackdata[pkmn.name]['moves']:
                                            trackdata[pkmn.name]['moves'][move['name']]=[]
                                        if pkmn.level not in trackdata[pkmn.name]['moves'][move['name']]:
                                            trackdata[pkmn.name]['moves'][move['name']].append(pkmn.level)
                                        # forces the moves to be shown in order of appearance rather than data order
                                        lvllist = {}
                                        for mv, lvl in trackdata[pkmn.name]['moves'].items():
                                            for k in lvl:
                                                lvllist.setdefault(k, set()).add(mv)
                                        currlvllist = list(lvllist[pkmn.level])
                                        # print(currlvllist)
                                        movect = currlvllist.index(move['name']) + 1
                                        # print(movect)
                                        window['-mv{}type-e-'.format(movect)].update(resize('images/categories/{}.png'.format(move["category"]), (27,20)), visible = True)
                                        window['-mv{}text-e-'.format(movect)].update(move["name"], text_color=typeformatting(move['type']), visible = True)
                                        window['-mv{}text-e-'.format(movect)].set_tooltip(move["description"])
                                        window['-mv{}pp-e-'.format(movect)].update('{}/{}'.format(int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1)), move["maxpp"]), visible = True)
                                        # window['-mv{}mod-e-'.format(movect)].update('images/modifiers/modifier{}.png'.format(modimage), visible = True)
                                        if stab == move['type']:
                                            window['-mv{}bp-e-'.format(movect)].update(movepower, text_color=typeformatting(move['type']), visible = True)
                                        else:
                                            window['-mv{}bp-e-'.format(movect)].update(movepower, text_color='white', visible = True)
                                        window['-mv{}acc-e-'.format(movect)].update(acc, visible = True)
                                        window['-mv{}ctc-e-'.format(movect)].update(contact, visible = True)
                                    emon = pkmn
                                pkmntypes=[]
                            elif (enctype=='p') and (pkmn.name == slotchoice):
                                ##### TYPES, STATS, ABIILITIES, ETC.
                                for type in pkmn.types:
                                    window['-typeimg{}-'.format(pkmn.types.index(type) + 1)].Update(resize('images/types/{}.png'.format(type[0]), (27, 24)), visible = True)
                                    window['-typename{}-'.format(pkmn.types.index(type) + 1)].Update('{}'.format(type[0]), text_color=typeformatting(type[0]), visible = True)
                                    if len(pkmn.types) == 1:
                                        window['-typeimg2-'].Update(visible = False)
                                        window['-typename2-'].Update(visible = False)
                                if pkmn.evo:
                                    evoitem = ('' if not pkmn.evoitem else 'w/'+pkmn.evoitem)
                                    evofriend = ('' if pkmn.evotype != 'Friendship' else 'w/ high friendship')
                                    evolevel = ('' if not pkmn.evolevel else '@ level '+str(int(pkmn.evolevel)))
                                    evostring = ('' if not pkmn.evostring else pkmn.evostring)
                                    evoloc = ('' if not pkmn.evolocation else 'in '+pkmn.evolocation)
                                if pkmn.status != '':
                                    window['-status-'].Update(resize('images/statuses/{}.png'.format(pkmn.status), (75, 20)), visible = True)
                                else:
                                    window['-status-'].Update(visible = False)
                                ### MOVES ########
                                totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                nmove = (' - ' if not nextmove else nextmove)
                                for move in pkmn.moves:
                                    stab = ''
                                    movetyp=movetype(pkmn,move,pkmn.held_item_num)
                                    for type in pkmn.types:
                                        if move['type'] == type[0]:
                                            stab = move['type']
                                            continue
                                    movepower = calcPower(pkmn,move)
                                    acc = '-' if not move['acc'] else int(move['acc'])
                                    contact = ('Y' if move['contact'] else 'N')
                                ### UPDATING TRACKER INFO ###
                                # print(slot)
                                attackchange,defchange,spatkchange,spdefchange,speedchange = pkmn.getStatChanges()
                                naturelist = [attackchange,defchange,spatkchange,spdefchange,speedchange]
                                query=f"""select
                                        itemname
                                        ,itemdesc
                                    from "generationitem" 
                                    where itemname = '{pkmn.held_item_name}' and genid <= {gen}
                                    """
                                itemname,itemdesc = cursor.execute(query).fetchone()
                                window['-slot-'].Update('Slot {} - {}'.format(str(party.index(pkmn)+1), 'Overworld'))
                                try:
                                    window['-monimg-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                except:
                                    window['-monimg-'].Update(visible = False)
                                    print(Exception)
                                window['-monname-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                window['-monnum-'].Update('#{}'.format(str(pkmn.species_num())))
                                window['-level-'].Update('Level: {}'.format(str(pkmn.level)))
                                window['-level-'].set_tooltip('Seen at {}'.format(trackdata[pkmn.name]["levels"]))
                                if pkmn.evo:
                                    window['-evo-'].update('>', visible = True)
                                    window['-evo-'].set_tooltip('Evolves {}{}{}{}{}'.format(evoitem, evofriend, evolevel, evostring, evoloc))
                                else:
                                    window['-evo-'].update(visible = False)
                                window['-ability-'].update(str(pkmn.ability['name']))
                                window['-ability-'].set_tooltip(str(pkmn.ability['description']))
                                window['-item-'].update(pkmn.held_item_name)
                                window['-item-'].set_tooltip(itemdesc)
                                window['-hplabel-'].update(visible = True)
                                window['-attlabel-'].update(visible = True, text_color=natureformatting(naturelist, 0))
                                window['-deflabel-'].update(visible = True, text_color=natureformatting(naturelist, 1))
                                window['-spattlabel-'].update(visible = True, text_color=natureformatting(naturelist, 2))
                                window['-spdeflabel-'].update(visible = True, text_color=natureformatting(naturelist, 3))
                                window['-speedlabel-'].update(visible = True, text_color=natureformatting(naturelist, 4))
                                window['-bstlabel-'].update(visible = True)
                                window['-hp-'].update('{}/{}'.format(pkmn.cur_hp, pkmn.maxhp))
                                window['-hp-'].set_tooltip('EV: ' + str(pkmn.evhp))
                                window['-att-'].update(pkmn.attack, text_color=natureformatting(naturelist, 0))
                                window['-att-'].set_tooltip('EV: ' + str(pkmn.evattack))
                                window['-def-'].update(pkmn.defense, text_color=natureformatting(naturelist, 1))
                                window['-def-'].set_tooltip('EV: ' + str(pkmn.evdefense))
                                window['-spatt-'].update(pkmn.spatk, text_color=natureformatting(naturelist, 2))
                                window['-spatt-'].set_tooltip('EV: ' + str(pkmn.evspatk))
                                window['-spdef-'].update(pkmn.spdef, text_color=natureformatting(naturelist, 3))
                                window['-spdef-'].set_tooltip('EV: ' + str(pkmn.evspdef))
                                window['-speed-'].update(pkmn.speed, text_color=natureformatting(naturelist, 4))
                                window['-speed-'].set_tooltip('EV: ' + str(pkmn.evspeed))
                                window['-bst-'].update(pkmn.bst)
                                window['-attmod-'].update('images/modifiers/modifier6.png')
                                window['-defmod-'].update('images/modifiers/modifier6.png')
                                window['-spattmod-'].update('images/modifiers/modifier6.png')
                                window['-spdefmod-'].update('images/modifiers/modifier6.png')
                                window['-speedmod-'].update('images/modifiers/modifier6.png')
                                window['-movehdr-'].update('Moves {}/{} ({})'.format(learnedcount, totallearn, nmove))
                                window['-movehdr-'].set_tooltip(learnstr)
                                window['-movepphdr-'].update('PP')
                                window['-movebphdr-'].update('BP')
                                window['-moveacchdr-'].update('Acc')
                                window['-movecontacthdr-'].update('C')
                                for move in pkmn.moves:
                                    stab = ''
                                    movetyp=movetype(pkmn,move,pkmn.held_item_num)
                                    for type in pkmn.types:
                                        if move['type'] == type[0]:
                                            stab = move['type']
                                            # print(stab)
                                            continue
                                    movepower = calcPower(pkmn,move)
                                    acc = '-' if not move['acc'] else int(move['acc'])
                                    contact = ('Y' if move['contact'] else 'N')
                                    window['-mv{}type-'.format(pkmn.moves.index(move) + 1)].update(resize('images/categories/{}.png'.format(move["category"]), (27,20)), visible = True)
                                    window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].update(move["name"], text_color=typeformatting(move['type']), visible = True)
                                    window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].set_tooltip(move["description"])
                                    window['-mv{}pp-'.format(pkmn.moves.index(move) + 1)].update('{}/{}'.format(move["pp"], move["maxpp"]), visible = True)
                                    window['-mv{}mod-'.format(pkmn.moves.index(move) + 1)].update('images/modifiers/modifier6.png', visible = True)
                                    if stab == move['type']:
                                        window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(movepower, text_color=typeformatting(move['type']), visible = True)
                                    else:
                                        window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(movepower, text_color='white', visible = True)
                                    window['-mv{}acc-'.format(pkmn.moves.index(move) + 1)].update(acc, visible = True)
                                    window['-mv{}ctc-'.format(pkmn.moves.index(move) + 1)].update(contact, visible = True)
                                    continue
                                # making enemy mon stuff invisible when not in a battle
                                window['-tc1a-e-'].update(visible = False)
                                window['-tc2a-e-'].update(visible = False)
                                window['-tc3a-e-'].update(visible = False)
                                window['-bc1a-e-'].update(visible = False)
                                window['-bc2a-e-'].update(visible = False)
                                # window['-bc3a-e-'].Update(visible = False)
                                window['-bc4a-e-'].update(visible = False)
                                window['-bc5a-e-'].update(visible = False)
                                window['-bc6a-e-'].update(visible = False)
                                window['-bc7a-e-'].update(visible = False)
                                ct = 0
                                while ct < 4:
                                    ct += 1
                                    window['-mv{}type-e-'.format(ct)].update(visible = False)
                                    window['-mv{}text-e-'.format(ct)].update(visible = False)
                                    window['-mv{}pp-e-'.format(ct)].update(visible = False)
                                    window['-mv{}mod-e-'.format(ct)].update(visible = False)
                                    window['-mv{}bp-e-'.format(ct)].update(visible = False)
                                    window['-mv{}acc-e-'.format(ct)].update(visible = False)
                                    window['-mv{}ctc-e-'.format(ct)].update(visible = False)
                            pk=pk+1
                    with open(trackadd,'w') as f:
                        json.dump(trackdata,f)
                    # if trackdataedit == 1:
                    #     with open(trackadd,'w') as f:
                    #         json.dump(trackdata,f)
                    #     trackdataedit = 0
                    # time.sleep(8.5)
            except Exception as e:
                print(e)
                with open('errorlog.txt','a+') as f:
                    errorLog = str(datetime.now())+": "+str(e)+'\n'
                    f.write(errorLog)
                # traceback.print_exc()
                import sys, os, traceback
                exc_type, exc_obj, exc_tb = sys.exc_info()
                tb = traceback.extract_tb(exc_tb)[-1]
                print(exc_type, tb[2], tb[1])
                time.sleep(5)
                print(errorLog)
                if "WinError 10054" in str(e):
                    print("To continue using the tracker, please open a ROM.")
                    print("Waiting for a ROM...")
                    time.sleep(15)
    except Exception as e:
        print(e)
        with open('errorlog.txt','a+') as f:
            errorLog = str(datetime.now())+": "+str(e)+'\n'
            f.write(errorLog)
        import sys, os, traceback
        exc_type, exc_obj, exc_tb = sys.exc_info()
        tb = traceback.extract_tb(exc_tb)[-1]
        print(exc_type, tb[2], tb[1])
        if "cannot unpack non-iterable NoneType object" in str(e):
            print("Waiting for a starter...")
            time.sleep(15)
    finally:
        print("")

BLOCK_SIZE = 56
SLOT_OFFSET = 484
SLOT_DATA_SIZE = (8 + (4 * BLOCK_SIZE))
STAT_DATA_OFFSET = 112
STAT_DATA_SIZE = 22

conn = sqlite3.connect("data/gen67.sqlite")
cursor = conn.cursor()

with open('data/item-data.json','r') as f:
    items = json.loads(f.read())

if __name__ == "__main__" :
    run()