import struct
import time
import os
import subprocess
import sys
import json
import sqlite3
import traceback
# from configparser import ConfigParser
from datetime import datetime
import logging
from citra import Citra
import re
import os
from io import BytesIO
import pathlib
from contextlib import contextmanager

@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:  
            yield
        finally:
            sys.stdout = old_stdout

def install(package):
    print(f'Installing [{package}]')
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print(f'Installed package [{package}].')

# deprecating using "official" PSG due to paywall - will keep code around just in case other bullshit happens
# try: # check for PySimpleGUI and install if not present
#     import PySimpleGUI as sg
#     if sg.__version__ != '4.60.5':
#         print('Incorrect version of PSG package detected - installing PySimpleGUI v4.60.5.')
#         subprocess.check_call([sys.executable, "-m", "pip", "install", '--force-reinstall', '-v', 'PySimpleGUI==4.60.5'])
#         print('Update complete.')
#         import PySimpleGUI as sg
# except:
#     install('PySimpleGUI==4.60.5') # pysimplegui apparently requires a license for v5.+, so i'm locking it to 4.60.5, which is what i'm developing on
#     import PySimpleGUI as sg

try: # check for FreeSimpleGUI and install if not present
    import FreeSimpleGUI as sg
except:
    install('FreeSimpleGUI==5.1.0')
    import FreeSimpleGUI as sg

try: # check for Pillow and install if not present
    from PIL import Image
except:
    install('Pillow==10.1.0')
    from PIL import Image

try: # check for requests and install if not present
    import requests
except:
    install('requests==2.31.0')
    import requests

try: # check for requests and install if not present
    import pandas as pd
except:
    install('pandas==2.2.1')
    import pandas as pd

from util.gitcheck import gitcheck
from util.notesclear import notesclear, notesclear_solo
from util.settings import autoload_settings, settings_load
from util.bagfuncs import bagitems
from util.uisettings import defaultuisettings
import util.logreader as lr
from util.logreadersolo import logloader_solo

# pysimplegui settings et al
track_title = 'Ironmon Tracker'
scale = 1.3
track_size = (600, 600)
font_sizes = [14, 11, 9, 15, 12]
sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=100, scaling=scale, element_padding=(2,2,2,2), suppress_error_popups=True)
refresh_rate = 4000

curr_version = open('version.txt', 'r').read()
gitcheck(curr_version)

trackadd=r"trackerdata.json"
# will also need to try/except some of this as well
# settingsfile=r"settings.json"
settingsfile=settings_load()

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
        # print("form",form,"dex",dex)
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
            case 25: # Pikachu partner forms
                match form:
                    case 0 | 2:
                        query+= " and pokemonsuffix is null"
                    case _: # no idea how many partner forms there are, but they're all here apparently
                        query+= " and pokemonsuffix is partner"
            case 150: ### Mewtwo
                match form:
                    case 4:
                        query+= " and pokemonsuffix is null"
                    case 12:
                        query+= " and pokemonsuffix = 'mega-x'"
                    case 20: ### Mewtwo Y
                        query+= " and pokemonsuffix = 'mega-y'"
            case 151: ### Mew, not honestly sure why this one is weird
                query+= " and pokemonsuffix is null"
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
                    case 4:
                        query+= " and pokemonsuffix is null"
                    case 12:
                        query+= " and pokemonsuffix = 'attack'"
                    case 20:
                        query+= " and pokemonsuffix = 'defense'"
                    case 28:
                        query+= " and pokemonsuffix = 'speed'"
            case 412: ### Burmy
                query+= " and pokemonsuffix is null"
            case 413: ### Wormadam
                match form:
                    case 10:
                        query+= " and pokemonsuffix = 'sandy'"
                    case 18:
                        query+= " and pokemonsuffix = 'trash'"
                    case 2:
                        query+= " and pokemonsuffix = 'plant'"
            case 414: ### Mothim
                query+= " and pokemonsuffix is null"
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
            case 550: ### Basculin
                query+= " and pokemonsuffix is null"
            case 555: ### Darmanitan
                match form:
                    case 0 | 2:
                        query+= " and pokemonsuffix is null"
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
            case 664: ### Scatterbug
                query+= " and pokemonsuffix is null"
            case 665: ### Spewpa
                query+= " and pokemonsuffix is null"
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
                    case 0 | 8:
                        query+= " and pokemonsuffix is null"
                    case 10:
                        query+= " and pokemonsuffix = 'f'"
            case 681: ### Aegislash
                match form:
                    case 0 | 2:
                        query+= " and pokemonsuffix = 'shield'"
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'blade'"
            case 710: ### Pumpkaboo
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'average'"
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'large'"
                    case 24 | 26:
                        query+= " and pokemonsuffix = 'super'"
                    case _:
                        query+= " and pokemonsuffix is null"
            case 711: ### Gourgeist
                match form:
                    case 8 | 10:
                        query+= " and pokemonsuffix = 'average'"
                    case 16 | 18:
                        query+= " and pokemonsuffix = 'large'"
                    case 24 | 26:
                        query+= " and pokemonsuffix = 'super'"
                    case _:
                        query+= " and pokemonsuffix is null"
            case 716: ### Xerneas
                query+= " and pokemonsuffix is null"
            case 718: ### Zygarde only needed for gen 7
                match form:
                    case 4:
                        query+= " and pokemonsuffix is null"
                    case 12:
                        query+= " and pokemonsuffix = '10'"
                    case 20 | 36:
                        query+= " and pokemonsuffix = 'complete'"
            case 720: ### Hoopa
                match form:
                    case 4:
                        query+= " and pokemonsuffix is null"
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
                    case _:
                        query+= " and pokemonsuffix = 'baile'"
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
                    case 4:
                        query+= " and pokemonsuffix is null"
                    case 12:
                        query+= " and pokemonsuffix = 'dusk'"
                    case 20:
                        query+= " and pokemonsuffix = 'dawn'"
                    case 28:
                        query+= " and pokemonsuffix = 'ultra'"
            case 801: ### Magearna
                query+= " and pokemonsuffix is null"
            case 19 | 20 | 26 | 27 | 28 | 37 | 38 | 50 | 51 | 52 | 53 | 74 | 75 | 76 | 88 | 89 | 103 | 105: ###alolan forms-none have separate forms so just case them for if their form > 0
                match form:
                    case 8 | 10 | 12: # honestly not sure if any are genderless but sure
                        query+= " and pokemonsuffix is 'alola'"
                    case _:
                        query+= " and pokemonsuffix is null"
            # case 81 | 82 | 100 | 101 | 120 | 121 | 137 | 233 | 292 | 337 | 338 | 343 | 344 | 374 | 375 | 376 | 436 | 437 | 462 | 474 | 489 | 490 | 599 | 600 | 601 | 615 | 622 | 623 | 703 | 774 | 781 | 854 | 855 | 770 | 132 | 144 | 145 | 146 | 201 | 243 | 244 | 245 | 249 | 250 | 251 | 377 | 378 | 379 | 382 | 383 | 384 | 385 | 386 | 480 | 481 | 482 | 483 | 484 | 486 | 491 | 493 | 494 | 638 | 639 | 640 | 643 | 644 | 646 | 647 | 649 | 716 | 717 | 718 | 719 | 721: ### Genderless exceptions
            #     query+= " and pokemonsuffix is null"
            case _:
                if form == 2: ### female
                    query+= " and pokemonsuffix is null"
                elif form == 4: ### genderless
                    query+= " and pokemonsuffix is null"
                elif form > 0:
                    query+= " and pokemonsuffix ='mega'"
                else:
                    query+= " and pokemonsuffix is null"
        # print(query)
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
        self.held_item_name = items[self.held_item_num]['name']
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
                                                        WHERE gamegrouporder <= (
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
        if learnlist==[]:
            mainmonmovequery=int(cursor.execute(f"""SELECT pokemonid FROM "pokemon.pokemon" WHERE pokemonpokedexnumber = "{self.species_num()}" AND pokemonsuffix ISNULL """ ).fetchone()[0])
            learnlist=cursor.execute(f"""select pokemonmovelevel
                from "pokemon.pokemonmove" pm
                    left join "pokemon.pokemonmovemethod" pmm on pm.pokemonmovemethodid = pmm.pokemonmovemethodid
                    where gamegroupid <= {gamegroupid}
                        and pokemonmovemethodname = 'Level up'
                        and pokemonmovelevel > 1
                        and pokemonid = {mainmonmovequery}
                    order by pokemonmovelevel""").fetchall()
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
    return ""

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
        multippadd=136331232+20784
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
        multippadd=0x8CF727C-0xAF2F5C-20+6928+20784
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
        multippadd=wildppadd
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
        multippadd=wildppadd
        mongap=816
    else:
        return -1,-1,-1,-1,-1,-1
    
    if read_party(c,battlewildoppadd)[0].species_num() in range(1,808) and int.from_bytes(c.read_memory(wildppadd,1))<65:
        return battlewildpartyadd,battlewildoppadd,wildppadd,curoppadd,'w',mongap
    elif read_party(c,battletraineroppadd)[0].species_num() in range(1,808) and int.from_bytes(c.read_memory(trainerppadd,1))<65:
        return battletrainerpartyadd,battletraineroppadd,trainerppadd,curoppadd,'t',mongap
    # elif read_party(c,battletraineroppadd)[0].species_num() in range(1,808) and int.from_bytes(c.read_memory(multippadd,1)) in range(1,65):
    #     return battletrainerpartyadd,battletraineroppadd,multippadd,curoppadd,'m',mongap
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

def calcPower(pkmn,move,hp1,hp2,pkmnwt,enwt):
    if move['name'] in ('Eruption','Water Spout'):
        return int(int(hp1)/int(hp2)*150)
    elif move['name']=='Return':
        return round(pkmn.friendship/2.5)
    elif move['name']=="Frustration":
        return round((255-pkmn.friendship)/2.5)
    elif move["name"] in ("Low Kick","Grass Knot"):
        try:
            weightnum=cursor.execute(enwt).fetchone()[0]
            if weightnum>=200:
                return 120
            elif 100<=weightnum<200:
                return 100
            elif 50<=weightnum<100:
                return 80
            elif 25<=weightnum<50:
                return 60
            elif 10<=weightnum<25:
                return 40
            else:
                return 20
        except:
            return "WT"
    elif move["name"] in ("Heat Crash","Heavy Slam"):
        try:
            weightnum=cursor.execute(enwt).fetchone()[0]
            weightratio=(pkmnwt/weightnum)
            if weightratio>=5:
                return 120
            elif 4<=weightratio<5:
                return 100
            elif 3<=weightratio<4:
                return 80
            elif 2<=weightratio<3:
                return 60
            else:
                return 40
        except:
            return "WT"
    elif move['name']=="Fling":
        return "ITEM"
    elif move['name'] in ("Crush Grip","Wring Out"):
        return ">HP"
    elif move['name'] in ("Flail","Reversal"):
        if int(hp1)/int(hp2)>=.6875:
            return 20
        elif int(hp1)/int(hp2)>=.3542:
            return 40
        elif int(hp1)/int(hp2)>=.2083:
            return 80
        elif int(hp1)/int(hp2)>=.1042:
            return 100
        elif int(hp1)/int(hp2)>=.0417:
            return 150
        elif int(hp1)/int(hp2)<.0417:
            return 200
        else:
            return "ERR"
    elif move['name'] == 'Psywave':
        return 'VAR'
    elif move['name'] in ('Seismic Toss', 'Night Shade'):
        return 'LVL'
    elif move['name'] in ('Electro Ball', 'Gyro Ball'):
        return 'SPD'
    elif move['name'] == 'Punishment':
        return '60+'
    else:
        return ('-' if not move['power'] else int(move['power']))
    
def calcAcc(move, pkmn1lvl, pkmn2lvl):
    if move['name'] in ('Horn Drill', 'Sheer Cold', 'Guillotine', 'Fissure'):
        if pkmn1lvl >= pkmn2lvl:
            a = 30 + pkmn1lvl - pkmn2lvl
            return a
        else:
            return 'X'
    elif not move['acc']:
        return '-'
    else: 
        return int(move['acc'])

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
    typecolordict = {'Normal':'#A8A878', 'Fire':'#F08030', 'Water':'#6890F0', 'Electric':'#F8D030', 'Grass':'#78C850', 
                  'Ice':'#98D8D8', 'Fighting':'#C03028', 'Poison':'#A040A0', 'Ground':'#E0C068', 'Flying':'#A890F0',
                  'Psychic':'#F85888', 'Bug':'#A8B820', 'Rock':'#B8A038', 'Ghost':'#705898', 'Dragon':'#7038F8', 
                  'Dark':'#705848', 'Steel':'#B8B8D0', 'Fairy':'#ffb1ff', 'Unknown':'#FFFFFF', None:"#FFFFFF"} #Fairy? EE99AC
    # typecolordict = {'Normal':'#999999', 'Fire':'#ff612c', 'Water':'#2892ff', 'Electric':'#ffdb00', 'Grass':'#42bf24', 
    #               'Ice':'#42bfff', 'Fighting':'#ffa202', 'Poison':'#994dcf', 'Ground':'#ab7939', 'Flying':'#95c9ff',
    #               'Psychic':'#ff637f', 'Bug':'#9fa523', 'Rock':'#bcb889', 'Ghost':'#6e4570', 'Dragon':'#7e44ed', 
    #               'Dark':'#2f4f4f', 'Steel':'#708090', 'Fairy':'#ffb1ff'}
    typecolor = typecolordict.get(typing, '#FFFFFF')
    return typecolor

def natureformatting(nl, s):
    naturedict = {'raised':'#80f080', 'lowered':'#f08080', 'neutral':'#ffffff'}
    if nl[s] == 'raised':
        return naturedict['raised']
    elif nl[s] == 'lowered':
        return naturedict['lowered']
    else:
        return naturedict['neutral']
    
def natureberries(nl):
    dislikedflavor = {'spicy':'Figy Berry', 'dry':'Wiki Berry', 'sweet':'Mago Berry', 'bitter':'Aguav Berry', 'sour':'Iapapa Berry', 'neutral':'No berry'}
    if nl[0] == 'lowered':
        s = '-attlabel-'
        return dislikedflavor['spicy'], s
    elif nl[1] == 'lowered':
        s = '-deflabel-'
        return dislikedflavor['sour'], s
    elif nl[2] == 'lowered':
        s = '-spattlabel-'
        return dislikedflavor['dry'], s
    elif nl[3] == 'lowered':
        s = '-spdeflabel-'
        return dislikedflavor['bitter'], s
    elif nl[4] == 'lowered':
        s = '-speedlabel-'
        return dislikedflavor['sweet'], s
    else:
        s = '-bstlabel-'
        return dislikedflavor['neutral'], s

def statnotes(s, pos):
    nt = s['stats'][pos]
    if nt == ' ':
        s['stats'][pos] = '+'
        txtcol = '#80f080'
    elif nt == '+':
        s['stats'][pos] = '-'
        txtcol = '#f08080'
    elif nt == '-':
        s['stats'][pos] = '='
        txtcol = '#ffffff'
    elif nt == '=':
        s['stats'][pos] = ' '
        txtcol = '#ffffff'
    return s, txtcol

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

    # print('[GUI_POPUP] event:', event)
    # print('[GUI_POPUP] values:', values)

    if values and values['-abilpopup-']:
        return values['-abilpopup-']

def run():
    try:
        #print('connecting to citra')
        c = Citra()
        #print('connected to citra')
        loops = 0
        l = 1 # corresponding layout
        slotchoice, slotlevel = '', 1
        enemymon, enemylevel = '', 1
        enemydict = {"abilities": [], "stats": ["", "", "", "", "", ""], "notes": "", "levels": [], "moves": []}
        change = ''
        hphl, statushl, pphl = '', '', ''
        frisk, antici = 0, 0
        try:
            seed = int(open('seed.txt', 'r').read())
        except:
            seed = 1
            with open('seed.txt','w+') as f:
                json.dump(seed,f)
        try:
            settingsdict=json.load(open(settingsfile,"r+"))
            batch_folder = pathlib.Path(str(settingsdict['batch_path']).strip())
            prefix = str(settingsdict['prefix']).strip()
        except:
            settingsdict = {'batch_path':'', 'mod_path':'', 'prefix':''}
            print('Set up your settings file.')
        pkmn_srch = 0

        game = ""
        print('Waiting for game to start...')
        while game == "":
            game=getGame(c)
            if game != "":
                gamegroupid,gamegroupabbreviation,gen = cursor.execute(f"""
                        select
                            gg.gamegroupid
                            ,gg.gamegroupabbreviation
                            ,gg.generationid
                        from "pokemon.gamegroup" gg
                        where gamegroupname = '{game}'""").fetchone()
        print('Game loaded: {}'.format(game))

        if game == 'X/Y':
            gameabbr = 'XY'
        elif game == 'OmegaRuby/AlphaSapphire':
            gameabbr = 'ORAS'
        elif game == 'Sun/Moon':
            gameabbr = 'SM'
        elif game == 'UltraSun/UltraMoon':
            gameabbr = 'USUM'
        else:
            gameabbr = 'Error'
        
        ## will need a bunch of try/excepts for this but for now lets get something functionally in place
        try:
            log = open((batch_folder / f'{prefix}{str(seed)}.log'), encoding="utf8").read()
            log_pkmn, log_wilds, log_tms, log_tmcompat, log_gen, log_game, log_trainer = lr.log_parser(log)
            if log_game != game:
                layout_logview = [[]] 
                print('Log and game do not match. Loading without native log reading functionality.')
                raise Exception
            graph = sg.Graph(canvas_size=(380,200), graph_bottom_left=(50,10), graph_top_right=(330,240),background_color='black', enable_events=True, key='-log-graph-')
            t_dict, t_types, log_tlist, log_tparty1, log_tparty2, log_tparty3, t_names = lr.trainerlist(log_game, log_trainer)
            logmoves, mvlist = lr.movelist(log_pkmn.iloc[pkmn_srch,16:])
            logabils, alist = lr.abillist(log_pkmn.iloc[pkmn_srch])
            logevos, elist = lr.evolist(log_pkmn.iloc[pkmn_srch])
            logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = lr.tmlist(log_pkmn.iloc[pkmn_srch], log_game, log_tmcompat, log_tms)
            logpivotlocs, logpivotbase1, logpivotbase2, pivottext = lr.pivotlist(log_game, log_gen, log_wilds)
            t = t_types[1] #current trainer subclass selected (defaults to gym leaders/kahunas)
            layout_logview = lr.logviewer_layout(pkmn_srch, log_pkmn, log_gen, logtms1, logabils, logmoves, logevos, logpivotbase1, logpivotbase2, graph, logpivotlocs, logtms4, logtmsfull, t_types, log_tlist, log_tparty1, log_tparty2, log_tparty3, t_dict)
            with suppress_stdout(): # suppressing the spam of "YOU HAVEN'T FINALIZED THE GRAPH YET" messages
                lr.statchart(log_pkmn.iloc[pkmn_srch], graph)
            # print(log_pkmn, ';;;', layout_logview)
            # print(layout_logview)
        except Exception as e:
            layout_logview = [[]] #if there isn't a log present, turn off the log feature entirely
            with open('errorlog.txt','a+') as f: #print to log, but don't print the error to console
                errorLog = str(datetime.now())+": "+str(e)+'\n'
                f.write(errorLog)
            print('Log not found - if using LayeredFS and tracker seed advancement, check your batch gen.')
            print('Log viewer will be disabled.')
            time.sleep(5)

        ### SET UP TRACKER GUI ###
        layout_main = defaultuisettings(font_sizes, layout_logview) # main gui
        
        window = sg.Window(track_title, layout_main, track_size, element_padding=(1,1,0,0), background_color='black', resizable=True, finalize=True)

        if layout_logview != [[]]:
            lr.statchart(log_pkmn.iloc[pkmn_srch], graph)

        while (True):
            try:
                if c.is_connected():
                    if loops == 0:
                        trackdata=json.load(open(trackadd,"r+"))
                        settingsdict=json.load(open(settingsfile,"r+"))
                    event, values = window.Read(timeout=refresh_rate)
                    if event == sg.WIN_CLOSED:
                        break
                    elif event == '-slotdrop-':
                        slotchoice = values['-slotdrop-']
                        window['-slotdrop-'].widget.select_clear()
                    elif event == '-hp-e-':
                        u, col = statnotes(enemydict, 0)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-hp-e-'].update('[{}]'.format(u['stats'][0]), text_color = col)
                    elif event == '-att-e-':
                        u, col = statnotes(enemydict, 1)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-att-e-'].update('[{}]'.format(u['stats'][1]), text_color = col)
                    elif event == '-def-e-':
                        u, col = statnotes(enemydict, 2)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-def-e-'].update('[{}]'.format(u['stats'][2]), text_color = col)
                    elif event == '-spatt-e-':
                        u, col = statnotes(enemydict, 3)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-spatt-e-'].update('[{}]'.format(u['stats'][3]), text_color = col)
                    elif event == '-spdef-e-':
                        u, col = statnotes(enemydict, 4)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-spdef-e-'].update('[{}]'.format(u['stats'][4]), text_color = col)
                    elif event == '-speed-e-':
                        u, col = statnotes(enemydict, 5)
                        trackdata[enemymon]['stats'] = u['stats']
                        window['-speed-e-'].update('[{}]'.format(u['stats'][5]), text_color = col)
                    elif event == '-addnote-e-':
                        note = sg.popup_get_text('Enter note:', title='Note', default_text=enemydict['notes'])
                        trackdata[enemymon]['notes'] = note
                        window['-note-e-'].update(trackdata[enemymon]['notes'])
                    elif event == '-addabil-e-':
                        abil = sg.popup_get_text('Enter ability:', title='Ability')
                        if abil != abil:
                            abil = ''
                        trackdata[enemymon]['abilities'].append(abil)
                        window['-abillist-e-'].update(trackdata[enemymon]['abilities'])
                        window['-ability-e-'].update(abil, text_color="#f0f080")
                        change = 'abil'
                    elif event == '-remabil-e-':
                        remabil = abil_popup(enemydict['abilities'])
                        trackdata[enemymon]['abilities'].remove(remabil)
                        window['-abillist-e-'].update(trackdata[enemymon]['abilities'])
                    elif event == '-hpheals-':
                        # making stuff readable
                        h = hphl
                        del h['percent']
                        h1 = f'HP Heals:\n{str(h).replace("'", '').replace('{', '').replace('}', '').title()}'
                        h2 = f'Status Heals:\n{str(statushl).replace("'", '').replace('{', '').replace('}', '').title()}'
                        h3 = f'PP Heals:\n{str(pphl).replace("'", '').replace('{', '').replace('}', '').title()}'
                        sg.popup_ok(h1, h2, h3, title='Healing Items')
                    elif event == '-settings-':
                        autoload_settings()
                    elif event == '-clearnotes-solo-':
                        confirm = sg.popup_ok_cancel('Reset tracker data?', title='Confirm')
                        if confirm == 'OK':
                            seed = notesclear_solo()
                            trackdata = json.load(open(trackadd,"r+"))
                        else:
                            continue
                    elif event == '-clearnotes-':
                        confirm = sg.popup_ok_cancel('Load next seed?\nAfter clicking yes, wait 1 sec then Citra > Emulation > Restart.', title='Confirm')
                        if confirm == 'OK':
                            seed = notesclear()
                            trackdata=json.load(open(trackadd,"r+"))
                            slotchoice = ''
                            window['-ph1-'].update('Waiting for new mon...', visible=True)
                            # clearing visual tracker info
                            window['-ability-'].update('')
                            window['-item-'].update('')
                            window['-hpheals-'].update('')
                            window['-tc2-'].update(visible = False)
                            window['-tc2b-'].update(visible = False)
                            window['-tc3-'].update(visible = False)
                            window['-bc1-'].update(visible = False)
                            window['-bc2-'].update(visible = False)
                            window['-bc4-'].update(visible = False)
                            window['-bc5-'].update(visible = False)
                            window['-bc6-'].update(visible = False)
                            window['-tc1a-e-'].update(visible = False)
                            window['-tc2-e-'].update(visible = False)
                            window['-bc1a-e-'].update(visible = False)
                            window['-bc2a-e-'].update(visible = False)
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
                            time.sleep(8)
                            try:
                                # need to fire up the log for the next one
                                pkmn_srch = 0
                                i = 0
                                log = open((batch_folder / f'{prefix}{str(seed)}.log'), encoding="utf8").read()
                                log_pkmn, log_wilds, log_tms, log_tmcompat, log_gen, log_game, log_trainer = lr.log_parser(log)
                                graph.Erase()
                                lr.statchart(log_pkmn.iloc[pkmn_srch], graph)
                                t_dict, t_types, log_tlist, log_tparty1, log_tparty2, log_tparty3, t_names = lr.trainerlist(log_game, log_trainer)
                                logmoves, mvlist = lr.movelist(log_pkmn.iloc[pkmn_srch,16:])
                                logabils, alist = lr.abillist(log_pkmn.iloc[pkmn_srch])
                                logevos, elist = lr.evolist(log_pkmn.iloc[pkmn_srch])
                                logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = lr.tmlist(log_pkmn.iloc[pkmn_srch], log_game, log_tmcompat, log_tms)
                                logpivotlocs, logpivotbase1, logpivotbase2, pivottext = lr.pivotlist(log_game, log_gen, log_wilds)
                                t = t_types[1]
                                # layout_logview = lr.logviewer_layout(pkmn_srch, log_pkmn, log_gen, logtms1, logabils, logmoves, logevos, logpivotbase1, logpivotbase2, graph, logpivotlocs, logtms4, logtmsfull)
                                while i < len(tmtextfull):
                                    if i < len(mvlist):
                                        window[f'-log-ml{i}-'].update(mvlist[i], visible = True)
                                    elif i < len(logmoves) - 1:
                                        window[f'-log-ml{i}-'].update(visible = False)
                                    if i < len(alist) and i == 2:
                                        window[f'-log-al{i}-'].update(f'{alist.iloc[i]} (HA)', visible = True)
                                    elif i < len(alist):
                                        window[f'-log-al{i}-'].update(alist.iloc[i], visible = True)
                                    if i == 0:
                                        window[f'-log-evos-'].update(f'{elist}', visible = True)
                                    if i < len(tmtext):
                                        if tmdict[tmtext[i]] == False:
                                            window[f'-log-gymtm1{i}-'].update(f'{tmtext[i]}', text_color='white')
                                            window[f'-log-gymtm4{i}-'].update(f'{tmtext[i]}', text_color='white')
                                        elif tmdict[tmtext[i]] == True:
                                            window[f'-log-gymtm1{i}-'].update(f'{tmtext[i]}', text_color='#339ec4')
                                            window[f'-log-gymtm4{i}-'].update(f'{tmtext[i]}', text_color='#339ec4')
                                    if tmdictfull[tmtextfull[i]] == False:
                                        window[f'-log-fulltm{i}-'].update(f'{tmtextfull[i]}', text_color='white')
                                    elif tmdictfull[tmtextfull[i]] == True:
                                        window[f'-log-fulltm{i}-'].update(f'{tmtextfull[i]}', text_color='#339ec4')
                                    i += 1
                                continue
                            except:
                                print('No log found, continuing without log support. If you have just set up your settings file, please reload the tracker.')
                    elif event == f'-view-log-':
                        window[f'-lc-'].update(visible=False)
                        window[f'-rc-'].update(visible=False)
                        l = 1
                        # update log with the mon that's in slotchoice
                        # print(log_pkmn.loc[log_pkmn['NAME'] == slotchoice])
                        try:
                            p = log_pkmn.loc[log_pkmn['NAME'] == slotchoice].index[0]
                        except:
                            p = log_pkmn.loc[log_pkmn['NAME'] == 'Bulbasaur'].index[0] # probably able to get this better somewhere down the line but for now lets just have it load at #1
                        graph.Erase()
                        lr.statchart(log_pkmn.iloc[p], graph)
                        logmoves, mvlist = lr.movelist(log_pkmn.iloc[p,16:])
                        logabils, alist = lr.abillist(log_pkmn.iloc[p])
                        logevos, elist = lr.evolist(log_pkmn.iloc[p])
                        logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = lr.tmlist(log_pkmn.iloc[p], log_game, log_tmcompat, log_tms)
                        pkmn_srch = p
                        i = 0
                        while i < len(tmtextfull):
                            if i < len(mvlist):
                                window[f'-log-ml{i}-'].update(mvlist[i], visible = True)
                            elif i < len(logmoves) - 1:
                                window[f'-log-ml{i}-'].update(visible = False)
                            if i < len(alist) and i == 2:
                                window[f'-log-al{i}-'].update(f'{alist.iloc[i]} (HA)', visible = True)
                            elif i < len(alist):
                                window[f'-log-al{i}-'].update(alist.iloc[i], visible = True)
                            if i == 0:
                                window[f'-log-evos-'].update(f'{elist}', visible = True)
                            if i < len(tmtext):
                                if tmdict[tmtext[i]] == False:
                                    window[f'-log-gymtm1{i}-'].update(text_color='white')
                                    window[f'-log-gymtm4{i}-'].update(text_color='white')
                                elif tmdict[tmtext[i]] == True:
                                    window[f'-log-gymtm1{i}-'].update(text_color='#339ec4')
                                    window[f'-log-gymtm4{i}-'].update(text_color='#339ec4')
                            if tmdictfull[tmtextfull[i]] == False:
                                window[f'-log-fulltm{i}-'].update(text_color='white')
                            elif tmdictfull[tmtextfull[i]] == True:
                                window[f'-log-fulltm{i}-'].update(text_color='#339ec4')
                            i += 1
                        window['-log-tmpkmn-'].update(f'{log_pkmn.iloc[p,1]} ({sum(log_pkmn.iloc[p,3:9])} BST)')
                        # default tab that comes up is pokemon
                        window[f'-lognav-trainer{l}-'].update(text_color='white')
                        window[f'-lognav-pivot{l}-'].update(text_color='white')
                        window[f'-lognav-tm{l}-'].update(text_color='white')
                        window[f'-lognav-pkmn{l}-'].update(text_color='#f0f080')
                        window[f'-logviewer-'].update(visible=True)
                    elif event == f'-lognav-exit{l}-':
                        window[f'-log-layout{l}-'].update(visible=False)
                        window[f'-lognav-trainer{l}-'].update(text_color='white')
                        window[f'-lognav-pivot{l}-'].update(text_color='white')
                        window[f'-lognav-tm{l}-'].update(text_color='white')
                        l = 1
                        window[f'-log-layout{l}-'].update(visible=True)
                        window[f'-lognav-pkmn{l}-'].update(text_color='#f0f080')
                        window[f'-logviewer-'].update(visible=False)
                        window[f'-lc-'].update(visible=True)
                        window[f'-rc-'].update(visible=True)
                    elif event == f'-lognav-pkmn{l}-':
                        window[f'-log-layout{l}-'].update(visible=False)
                        window[f'-lognav-trainer{l}-'].update(text_color='white')
                        window[f'-lognav-pivot{l}-'].update(text_color='white')
                        window[f'-lognav-tm{l}-'].update(text_color='white')
                        l = 1
                        window[f'-log-layout{l}-'].update(visible=True)
                        window[f'-lognav-pkmn{l}-'].update(text_color='#f0f080')
                    elif event == f'-lognav-trainer{l}-':
                        window[f'-log-layout{l}-'].update(visible=False)
                        window[f'-lognav-pkmn{l}-'].update(text_color='white')
                        window[f'-lognav-pivot{l}-'].update(text_color='white')
                        window[f'-lognav-tm{l}-'].update(text_color='white')
                        l = 2
                        window[f'-log-layout{l}-'].update(visible=True)
                        window[f'-lognav-trainer{l}-'].update(text_color='#f0f080')
                    elif event == f'-lognav-pivot{l}-':
                        window[f'-log-layout{l}-'].update(visible=False)
                        window[f'-lognav-trainer{l}-'].update(text_color='white')
                        window[f'-lognav-pkmn{l}-'].update(text_color='white')
                        window[f'-lognav-tm{l}-'].update(text_color='white')
                        l = 3
                        window[f'-log-layout{l}-'].update(visible=True)
                        window[f'-lognav-pivot{l}-'].update(text_color='#f0f080')
                    elif event == f'-lognav-tm{l}-':
                        window[f'-log-layout{l}-'].update(visible=False)
                        window[f'-lognav-trainer{l}-'].update(text_color='white')
                        window[f'-lognav-pivot{l}-'].update(text_color='white')
                        window[f'-lognav-pkmn{l}-'].update(text_color='white')
                        l = 4
                        window[f'-log-layout{l}-'].update(visible=True)
                        window[f'-lognav-tm{l}-'].update(text_color='#f0f080')
                    # elif event == f'-lognav-tutor{l}-':
                        # window[f'-log-layout{l}-'].update(visible=False)
                        # window[f'-lognav-trainer{l}-'].update(color='white')
                        # window[f'-lognav-pivot{l}-'].update(color='white')
                        # window[f'-lognav-tm{l}-'].update(color='white')
                        # l = 5
                        # window[f'-lognav-tutor{l}-'].update(color='#f0f080')
                        # window[f'-log-layout{l}-'].update(visible=True)
                    # elif event == f'-lognav-info{l}-':
                        # window[f'-log-layout{l}-'].update(visible=False)
                        # window[f'-lognav-trainer{l}-'].update(color='white')
                        # window[f'-lognav-pivot{l}-'].update(color='white')
                        # window[f'-lognav-tm{l}-'].update(color='white')
                        # l = 6
                        # window[f'-lognav-info{l}-'].update(color='#f0f080')
                        # window[f'-log-layout{l}-'].update(visible=True)
                    elif event == f'-lognav-search{l}-':
                        p = lr.searchfcn(log_pkmn, pkmn_srch)
                        graph.Erase()
                        lr.statchart(log_pkmn.iloc[p], graph)
                        logmoves, mvlist = lr.movelist(log_pkmn.iloc[p,16:])
                        logabils, alist = lr.abillist(log_pkmn.iloc[p])
                        logevos, elist = lr.evolist(log_pkmn.iloc[p])
                        logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = lr.tmlist(log_pkmn.iloc[p], log_game, log_tmcompat, log_tms)
                        pkmn_srch = p
                        i = 0
                        while i < len(tmtextfull):
                            if i < len(mvlist):
                                window[f'-log-ml{i}-'].update(mvlist[i], visible = True)
                            elif i < len(logmoves) - 1:
                                window[f'-log-ml{i}-'].update(visible = False)
                            if i < len(alist) and i == 2:
                                window[f'-log-al{i}-'].update(f'{alist.iloc[i]} (HA)', visible = True)
                            elif i < len(alist):
                                window[f'-log-al{i}-'].update(alist.iloc[i], visible = True)
                            if i == 0:
                                window[f'-log-evos-'].update(f'{elist}', visible = True)
                            if i < len(tmtext):
                                if tmdict[tmtext[i]] == False:
                                    window[f'-log-gymtm1{i}-'].update(text_color='white')
                                    window[f'-log-gymtm4{i}-'].update(text_color='white')
                                elif tmdict[tmtext[i]] == True:
                                    window[f'-log-gymtm1{i}-'].update(text_color='#339ec4')
                                    window[f'-log-gymtm4{i}-'].update(text_color='#339ec4')
                            if tmdictfull[tmtextfull[i]] == False:
                                window[f'-log-fulltm{i}-'].update(text_color='white')
                            elif tmdictfull[tmtextfull[i]] == True:
                                window[f'-log-fulltm{i}-'].update(text_color='#339ec4')
                            i += 1
                        window['-log-tmpkmn-'].update(f'{log_pkmn.iloc[p,1]} ({sum(log_pkmn.iloc[p,3:9])} BST)')
                    elif event in ('-logpivot-loc0-', '-logpivot-loc1-', '-logpivot-loc2-', '-logpivot-loc3-', '-logpivot-loc4-'):
                        n = int(event[-2:].replace('-',''))
                        for i in range(0, len(logpivotlocs)-1): # turn off all different colors, then turn on for current
                            window[f'-logpivot-loc{i}-'].update(text_color='white')
                        window[event].update(text_color='#f0f080')
                        for j in range(1, len(logpivotbase1)): #update rows with loc info, length of the pivotbase is number of mons + 1 due to the header
                            window[f'-logpivot-mon{j}-'].update(pivottext[f'{n}-{j}'][0], visible = True)
                            window[f'-logpivot-lvl{j}-'].update(pivottext[f'{n}-{j}'][1], visible = True)
                    elif event in ('-log-train-rival-', '-log-train-leader-', '-log-train-e4-', '-log-train-other-'):
                        window['-log-train-rival-'].update(text_color='white')
                        window['-log-train-leader-'].update(text_color='white')
                        window['-log-train-e4-'].update(text_color='white')
                        window['-log-train-other-'].update(text_color='white')
                        window[event].update(text_color='#f0f080')
                        if event == '-log-train-rival-':
                            t = t_types[0]
                            lr.set_size(window['-log-tcol-0-'], (120, 400))
                            lr.set_size(window['-log-tcol-1-'], (0, 400))
                            lr.set_size(window['-log-tcol-2-'], (0, 400))
                            lr.set_size(window['-log-tcol-3-'], (0, 400))
                        elif event == '-log-train-leader-':
                            t = t_types[1]
                            lr.set_size(window['-log-tcol-0-'], (0, 400))
                            lr.set_size(window['-log-tcol-1-'], (120, 400))
                            lr.set_size(window['-log-tcol-2-'], (0, 400))
                            lr.set_size(window['-log-tcol-3-'], (0, 400))
                        elif event == '-log-train-e4-':
                            t = t_types[2]
                            lr.set_size(window['-log-tcol-0-'], (0, 400))
                            lr.set_size(window['-log-tcol-1-'], (0, 400))
                            lr.set_size(window['-log-tcol-2-'], (120, 400))
                            lr.set_size(window['-log-tcol-3-'], (0, 400))
                        elif event == '-log-train-other-':
                            t = t_types[3]
                            lr.set_size(window['-log-tcol-0-'], (0, 400))
                            lr.set_size(window['-log-tcol-1-'], (0, 400))
                            lr.set_size(window['-log-tcol-2-'], (0, 400))
                            lr.set_size(window['-log-tcol-3-'], (120, 400))
                        for i in range(0, 6): # clearing previous tab's trainer data
                            window[f'-log-train-pkmnname-{i}-'].update('')
                            window[f'-log-train-pkmnitem-{i}-'].update('')
                            window[f'-log-train-pkmnlvl-{i}-'].update('')
                    elif event in ('-log-train-0-', '-log-train-1-', '-log-train-2-', '-log-train-3-', '-log-train-4-', '-log-train-5-', '-log-train-6-', '-log-train-7-', '-log-train-8-', '-log-train-9-', '-log-train-10-', '-log-train-11-', '-log-train-12-', '-log-train-13-', '-log-train-14-', '-log-train-15-', '-log-train-16-', '-log-train-17-'):
                        n = int(event[-3:].replace('-',''))
                        for i in range(0, len(log_tlist)):
                            window[f'-log-train-{i}-'].update(text_color='white')
                        window[event].update(text_color='#f0f080')
                        for i in range(0,6):
                            j = int(i * 2)
                            if t_dict[t][t_names[n]][1][j] == None: # if less than 6 mons
                                window[f'-log-train-pkmnname-{i}-'].update('')
                                window[f'-log-train-pkmnitem-{i}-'].update('')
                                window[f'-log-train-pkmnlvl-{i}-'].update('')
                            elif isinstance(t_dict[t][t_names[n]][1][j], list) == True: # check for held item
                                window[f'-log-train-pkmnname-{i}-'].update(t_dict[t][t_names[n]][1][j][0])
                                window[f'-log-train-pkmnitem-{i}-'].update(t_dict[t][t_names[n]][1][j][1])
                                window[f'-log-train-pkmnlvl-{i}-'].update(t_dict[t][t_names[n]][1][j+1])
                            else: # no held item
                                window[f'-log-train-pkmnname-{i}-'].update(t_dict[t][t_names[n]][1][j])
                                window[f'-log-train-pkmnitem-{i}-'].update('')
                                window[f'-log-train-pkmnlvl-{i}-'].update(t_dict[t][t_names[n]][1][j+1])
                    elif event in ('-load-log-'):
                        logloader_solo((380, 580))
                    partyadd,enemyadd,ppadd,curoppnum,enctype,mongap=getaddresses(c)
                    # print("loops" + str(loops))
                    loops+=1

                    # only continue reading data if a supported game is running
                    if partyadd == -1:
                        continue

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
                    abblist = []
                    for pkmn in party:
                        if pkmn in party1:
                            if pkmn.species_num()==0:
                                party1.remove(pkmn)
                            if pkmn.species_num()!=0:
                                pkmn.getAtts(gamegroupid,gen)
                                abblist.append(pkmn.ability['name'])
                    for pkmn in party2:
                        pkmni+=1
                        if pkmn.species_num()!=enemynum:
                            party.remove(pkmn)
                        else:
                            pkmnindex=(pkmni)
                            if enctype!="p":
                                pkmn.getAtts(gamegroupid,gen)
                                if pkmn.suffix!="":
                                    weightquery=f"""SELECT kg FROM "pokemon.weight" WHERE name = "{pkmn.name}" AND form = "{pkmn.suffix}" """ 
                                else: weightquery=f"""SELECT kg FROM "pokemon.weight" WHERE name = "{pkmn.name}" """ 
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
                            if 0 <= byte < len(typelist) and typelist[byte] not in enemytypes:
                                enemytypes.append(typelist[byte])
                    except Exception:
                        print(Exception)
                    slot = []
                    for pkmn in party:
                        if pkmn.species_num() in range (1,808): ### Make sure the slot is valid & not an egg
                            pkmn.getAtts(gamegroupid,gen)
                            if int(pkmn.cur_hp) > 750: ### Make sure the memory dump hasn't happened (or whatever causes the invalid values)
                                continue
                            if int(pkmn.level)>100:
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
                            try:
                                pkmn_srch = log_pkmn.loc[log_pkmn['NAME'] == slotchoice].index[0]
                            except:
                                if slotchoice == pkmn.name and layout_logview != [[]]:
                                    # pkmn_srch = 0
                                    pkmn_srch = log_pkmn.loc[log_pkmn['NUM'] == pkmn.species_num()].index[0]
                                    # print(pkmn.species_num())
                            window['-slotdrop-'].Update(values=slot, value=slotchoice, visible=True)
                            # print(c, ';;;', getGame(c), ';;;', pkmn, ';;;', items)
                            hphl, statushl, pphl = bagitems(c, getGame(c), pkmn, items)
                            # print(enctype, ';;;', pkmn.name, ';;;', party.index(pkmn)+1, ';;;', pkmnindex+12)
                            if enctype!='p':
                                #grabs in battle types
                                pkmntypes=[]
                                currmon = pkmn
                                typereader=c.read_memory(ppadd+(mongap*(pk-1))-(2*(gen+6)),2)
                                for byte in typereader:
                                    if 0 <= byte < len(typelist) and typelist[byte] not in pkmntypes:
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
                                        evofriend = ''
                                        evolevel = ''
                                        evostring = ''
                                        evoloc = ''
                                        if pkmn.name == 'Eevee':
                                            evoitem = 'Any stone'
                                        elif pkmn.name == 'Gloom':
                                            evoitem = 'Leaf Stone/Sun Stone'
                                        elif pkmn.name == 'Poliwhirl':
                                            evoitem = 'Water Stone/Kings Rock'
                                        elif pkmn.name == 'Clamperl':
                                            evoitem = 'Deep Sea Tooth/Deep Sea Scale'
                                        elif pkmn.name == 'Slowpoke':
                                            evoitem = 'Kings Rock/Level 37'
                                        elif pkmn.name == 'Kirlia':
                                            evoitem = 'Lvl 30/Dawn Stone (M)'
                                        # need to check snorunt
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
                                    slotlevel = levelnum
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
                                    # print(batabilnum, ';;;', gen)
                                    try: abilityname,abilitydescription = cursor.execute(query).fetchone()
                                    except: continue # if this errors then the data stream is invalid anyway
                                    ### STATS ########
                                    #print(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-264),1)))
                                    attackchange,defchange,spatkchange,spdefchange,speedchange = pkmn.getStatChanges()
                                    naturelist = [attackchange,defchange,spatkchange,spdefchange,speedchange]
                                    confuseberry, confusestat = natureberries(naturelist)
                                    ### MOVES ########
                                    totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    query=f"""select
                                            itemname
                                            ,itemdesc
                                        from "generationitem" 
                                        where itemname = '{pkmn.held_item_name}' and genid <= {gen}
                                        """
                                    itemname,itemdesc = cursor.execute(query).fetchone()
                                    window['-ph1-'].update('', visible=False)
                                    window['-slot-'].Update(f'Seed {seed} ({gameabbr})')
                                    try:
                                        window['-monimg-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                    except:
                                        window['-monimg-'].Update(visible = False)
                                        print(Exception)
                                    window['-tc2-'].update(visible = True)
                                    window['-tc2b-'].update(visible = True)
                                    window['-tc3-'].update(visible = True)
                                    window['-bc1-'].update(visible = True)
                                    window['-bc2-'].update(visible = True)
                                    window['-bc4-'].update(visible = True)
                                    window['-bc5-'].update(visible = True)
                                    window['-bc6-'].update(visible = True)
                                    window['-monname-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                    window['-monnum-'].Update('#{}'.format(str(pkmn.species_num())))
                                    window['-level-'].Update('Level: {}'.format(slotlevel))
                                    # window['-level-'].set_tooltip('Seen at {}'.format(trackdata[pkmn.name]["levels"]))
                                    window['-ability-'].Update(str(pkmn.ability['name']), text_color="#f0f080")
                                    window['-ability-'].set_tooltip(str(pkmn.ability['description']))
                                    window['-item-'].Update(pkmn.held_item_name)
                                    window['-item-'].set_tooltip(itemdesc)
                                    if gen == 6:
                                        window['-hpheals-'].update("Heals: "+str(hphl["percent"])+"% ("+str(hphl["total"])+")", visible = True, text_color="#f0f080")
                                        window['-hpheals-'].set_tooltip(f'Click to view in new window. \n' +
                                            f'HP Heals: {str(hphl).replace("'", '').replace('{', '').replace('}', '').title()}\n'+
                                            f'Status Heals: {str(statushl).replace("'", '').replace('{', '').replace('}', '').title()}\n'+
                                            f'PP Heals: {str(pphl).replace("'", '').replace('{', '').replace('}', '').title()}')
                                    else: # don't currently have support for gen 7 :<
                                        window['-hpheals-'].update(visible = False)
                                    window['-hplabel-'].update(visible = True)
                                    window['-attlabel-'].update(visible = True, text_color=natureformatting(naturelist, 0))
                                    window['-deflabel-'].update(visible = True, text_color=natureformatting(naturelist, 1))
                                    window['-spattlabel-'].update(visible = True, text_color=natureformatting(naturelist, 2))
                                    window['-spdeflabel-'].update(visible = True, text_color=natureformatting(naturelist, 3))
                                    window['-speedlabel-'].update(visible = True, text_color=natureformatting(naturelist, 4))
                                    window[confusestat].set_tooltip('{} causes confusion'.format(confuseberry))
                                    window['-bstlabel-'].Update(visible = True)
                                    window['-hp-'].Update('{}/{}'.format(hpnum[0], hpnum[1]))
                                    window['-att-'].Update(pkmn.attack, text_color=natureformatting(naturelist, 0))
                                    window['-def-'].Update(pkmn.defense, text_color=natureformatting(naturelist, 1))
                                    window['-spatt-'].Update(pkmn.spatk, text_color=natureformatting(naturelist, 2))
                                    window['-spdef-'].Update(pkmn.spdef, text_color=natureformatting(naturelist, 3))
                                    window['-speed-'].Update(pkmn.speed, text_color=natureformatting(naturelist, 4))

                                    # Update stat stage modifiers, and only apply if within proper range
                                    modatt = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-20),1))
                                    if 0 <= modatt <= 12:
                                        window['-attmod-'].Update('images/modifiers/modifier{}.png'.format(modatt), visible = True)
                                    moddef = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-19),1))
                                    if 0 <= moddef <= 12:
                                        window['-defmod-'].Update('images/modifiers/modifier{}.png'.format(moddef), visible = True)
                                    modspatt = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-18),1))
                                    if 0 <= modspatt <= 12:
                                        window['-spattmod-'].Update('images/modifiers/modifier{}.png'.format(modspatt), visible = True)
                                    modspdef = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-17),1))
                                    if 0 <= modspdef <= 12:
                                        window['-spdefmod-'].Update('images/modifiers/modifier{}.png'.format(modspdef), visible = True)
                                    modspeed = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-16),1))
                                    if 0 <= modspeed <= 12:
                                        window['-speedmod-'].Update('images/modifiers/modifier{}.png'.format(modspeed), visible = True)
                                    window['-accevalabel-'].update(visible = True, text_color='white')
                                    modacc = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-15),1))
                                    if 0 <= modacc <= 12:
                                        window['-accmod-'].Update('images/modifiers/modifier{}.png'.format(modacc), visible = True)
                                    window['-accevaph-'].update(visible = True)
                                    modeva = int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-14),1))
                                    if 0 <= modeva <= 12:
                                        window['-evamod-'].Update('images/modifiers/modifier{}.png'.format(modeva), visible = True)

                                    window['-bst-'].Update(pkmn.bst)
                                    window['-movehdr-'].update(f'Moves {learnedcount}/{totallearn} ({nmove})')
                                    window['-movehdr-'].set_tooltip(learnstr)
                                    window['-movepphdr-'].update('PP')
                                    window['-movebphdr-'].update('Pow')
                                    window['-moveacchdr-'].update('Acc')
                                    window['-movecontacthdr-'].update('C')
                                    if layout_logview != [[]]:
                                        window['-clearnotes-'].update(visible=True)
                                        window['-view-log-'].update(visible=True)
                                    else: 
                                        window['-clearnotes-solo-'].update(visible=True)
                                    window['-load-log-'].update(visible=True)
                                    window['-settings-'].update(visible=True)
                                    for move in pkmn.moves:
                                        stab = ''
                                        movetyp=movetype(pkmn,move,pkmn.held_item_num)
                                        for type in pkmn.types:
                                            if move['type'] == type[0]:
                                                stab = move['type']
                                                continue
                                        #defines the columns for the arrays corresponding to the type hit
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
                                        typedic={"Normal":0,"Fighting":1,"Flying":2,"Poison":3,"Ground":4,"Rock":5,"Bug":6,"Ghost":7,"Steel":8,"Fire":9,"Water":10,"Grass":11,"Electric":12,"Psychic":13,"Ice":14,"Dragon":15,"Dark":16,"Fairy":17,"Null":18}

                                        # interactions between abilities and typings
                                        if pkmn.ability['name'] == 'Scrappy':
                                            typetable['Normal'] = [1,1,1,1,1,.5,1,1,.5,1,1,1,1,1,1,1,1,1,1]
                                            typetable['Fighting'] = [2,1,.5,.5,1,2,.5,1,2,1,1,1,1,.5,2,1,2,.5,1]
                                        if move['type'] == 'Normal' and pkmn.ability['name'] == 'Aerilate':
                                            movetyp = 'Flying'
                                        if move['type'] == 'Normal' and pkmn.ability['name'] == 'Pixilate':
                                            movetyp = 'Fairy'
                                        if move['type'] == 'Normal' and pkmn.ability['name'] == 'Refrigerate':
                                            movetyp = 'Ice'
                                        if move['type'] == 'Normal' and pkmn.ability['name'] == 'Galvanize':
                                            movetyp = 'Electric'
                                        if pkmn.ability['name'] == 'Normalize':
                                            movetyp = 'Normal' #lolrip

                                        typemult=1
                                        if movetyp!=None:
                                            for type in enemytypes:
                                                typemult=typemult*(typetable[movetyp][typedic[type]])
                                        modimage="6"
                                        if move["category"]!="Non-Damaging":
                                            if typemult==.25:
                                                modimage="4"
                                            elif typemult==.5:
                                                modimage="5"
                                            # elif typemult==1:
                                            #     modimage="6"
                                            elif typemult==2:
                                                modimage="7"
                                                antici = 1
                                            elif typemult==4:
                                                modimage="8"
                                                antici = 1
                                            elif typemult==0:
                                                modimage="X"
                                        # movepower = calcPower(pkmn,move,hpnum[0],hpnum[1])
                                        # acc = '-' if not move['acc'] else int(move['acc'])
                                        if pkmn.suffix != "":
                                            weightquery2=f"""SELECT kg FROM "pokemon.weight" WHERE name = "{pkmn.name}" AND form = "{pkmn.suffix}" """ 
                                        else: 
                                            weightquery2=f"""SELECT kg FROM "pokemon.weight" WHERE name = "{pkmn.name}" """ 
                                        # print(weightquery2)
                                        pkmnweight=cursor.execute(weightquery2).fetchone()[0]
                                        print(pkmnweight)
                                        acc = calcAcc(move, slotlevel, enemylevel)
                                        contact = ('Y' if move['contact'] else 'N')
                                        window['-mv{}type-'.format(pkmn.moves.index(move) + 1)].update(resize('images/categories/{}.png'.format(move["category"]), (27,20)))
                                        window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].update(move["name"], text_color=typeformatting(movetyp))
                                        window['-mv{}text-'.format(pkmn.moves.index(move) + 1)].set_tooltip(move["description"])
                                        window['-mv{}pp-'.format(pkmn.moves.index(move) + 1)].update('{}/{}'.format(int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1)), int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+1+(14*(pkmn.moves).index(move)),1))))
                                        window['-mv{}mod-'.format(pkmn.moves.index(move) + 1)].update('images/modifiers/modifier{}.png'.format(modimage))
                                        if stab == movetyp:
                                            window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(calcPower(pkmn,move,hpnum[0],hpnum[1],pkmnweight,weightquery), text_color=typeformatting(movetyp))
                                        else:
                                            window['-mv{}bp-'.format(pkmn.moves.index(move) + 1)].update(calcPower(pkmn,move,hpnum[0],hpnum[1],pkmnweight,weightquery), text_color='white')
                                        window['-mv{}acc-'.format(pkmn.moves.index(move) + 1)].update(acc)
                                        window['-mv{}ctc-'.format(pkmn.moves.index(move) + 1)].update(contact)
                                elif (pkmn in party2) & (((gen == 6) & (party.index(pkmn)+1 == 7)) | ((gen == 7) & (party.index(pkmn)+1 == 7))): # this works for singles in XY, needs testing for all other games; only access first mon stuff, may want to figure out a way to include double battle (may not work for multis)
                                # elif ((pkmn in party2) & (party.index(pkmn)+1 == 7)) | ((enctype == 't') & (party.index(pkmn)+1 == 1)): # this works for singles in XY, needs testing for all other games; only access first mon stuff, may want to figure out a way to include double battle (may not work for multis)
                                    # print(pkmn.name, ';;;', pkmn.species, ';;;', party.index(pkmn)+1)
                                    if (emon != pkmn) & (emon == emon): # washing the data on mon change
                                        ct = 0
                                        antici = 0
                                        enemymon = pkmn.name
                                        enemydict = trackdata[pkmn.name]
                                        for ct in range(1,5):
                                            window['-mv{}type-e-'.format(ct)].update(visible = False)
                                            window['-mv{}text-e-'.format(ct)].update(visible = False)
                                            window['-mv{}pp-e-'.format(ct)].update(visible = False)
                                            window['-mv{}mod-e-'.format(ct)].update(visible = False)
                                            window['-mv{}bp-e-'.format(ct)].update(visible = False)
                                            window['-mv{}acc-e-'.format(ct)].update(visible = False)
                                            window['-mv{}ctc-e-'.format(ct)].update(visible = False)
                                        change = ''
                                    for type in pkmn.types:
                                        window['-typeimg{}-e-'.format(pkmn.types.index(type) + 1)].Update(resize('images/types/{}.png'.format(type[0]), (27, 24)), visible = True)
                                        window['-typename{}-e-'.format(pkmn.types.index(type) + 1)].Update('{}'.format(type[0]), text_color=typeformatting(type[0]), visible = True)
                                        if len(pkmn.types) == 1:
                                            window['-typeimg2-e-'].Update(visible = False)
                                            window['-typename2-e-'].Update(visible = False)
                                    if pkmn.evo:
                                        evofriend = ''
                                        evolevel = ''
                                        evostring = ''
                                        evoloc = ''
                                        if pkmn.name == 'Eevee':
                                            evoitem = 'Any stone'
                                        elif pkmn.name == 'Gloom':
                                            evoitem = 'Leaf Stone/Sun Stone'
                                        elif pkmn.name == 'Poliwhirl':
                                            evoitem = 'Water Stone/Kings Rock'
                                        elif pkmn.name == 'Clamperl':
                                            evoitem = 'Deep Sea Tooth/Deep Sea Scale'
                                        elif pkmn.name == 'Slowpoke':
                                            evoitem = 'Kings Rock/Level 37'
                                        elif pkmn.name == 'Kirlia':
                                            evoitem = 'Lvl 30/Dawn Stone (M)'
                                        # need to check snorunt
                                        else:
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
                                    enemylevel = levelnum
                                    if pkmn.status != '':
                                        window['-status-e-'].Update(resize('images/statuses/{}.png'.format(pkmn.status), (75, 20)), visible = True)
                                    else:
                                        window['-status-e-'].Update(visible = False)

                                    ### OLD ABILITY CODE ###
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
                                    if gen == 7:
                                        try: 
                                            abilityname,abilitydescription = cursor.execute(query).fetchone()
                                        except: 
                                            emon = ''
                                            continue # if this errors then the data stream is invalid anyway
                                    else:
                                        try: 
                                            abilityname,abilitydescription = cursor.execute(query).fetchone()
                                        except: 
                                            continue # if this errors then the data stream is invalid anyway
                                    startupabils=["Air Lock","Cloud Nine","Delta Stream","Desolate Land","Download","Drizzle","Drought","Forewarn","Imposter","Intimidate","Mold Breaker","Pressure","Primordial Sea","Sand Stream","Slow Start","Snow Warning","Teravolt","Turboblaze","Trace","Unnerve","Aura Break","Fairy Aura","Dark Aura",'Psychic Surge','Electric Surge','Misty Surge','Grassy Surge','Comatose']
                                    if frisk == 1:
                                        startupabils.append('Frisk')
                                    if antici == 1:
                                        startupabils.append('Anticipation')
                                    if abilityname in startupabils:
                                        window['-ability-e-'].Update(str(pkmn.ability['name']), text_color="#f0f080")
                                        window['-ability-e-'].set_tooltip(str(pkmn.ability['description']))
                                        if pkmn.abilityname not in trackdata[pkmn.name]['abilities']:
                                            trackdata[pkmn.name]['abilities'].append(pkmn.abilityname)
                                    elif change == 'abil':
                                        window['-ability-e-'].set_tooltip('')
                                    else:
                                        window['-ability-e-'].Update('Unknown Ability', text_color="#f0f080")
                                    
                                    ### NEW ABILITY CODE ###
                                    # try:
                                    #     abillookup = batabilnum
                                    #     if getGame()=="X/Y":
                                    #         abildatapoint=136334160-714472
                                    #         abillookup = int.from_bytes(c.read_memory(abildatapoint,1))
                                    #         # print(abillookup)
                                    #     elif getGame()=="OmegaRuby/AlphaSapphire":
                                    #         abildatapoint=135669536
                                    #         # abillookup = int.from_bytes(c.read_memory(abildatapoint,1))
                                    #     query=f"""select
                                    #             ab.abilityname
                                    #             ,abilitydescription
                                    #         from "pokemon.generationability" ga
                                    #             left join "pokemon.ability" ab on ga.abilityid = ab.abilityid
                                    #             left join "pokemon.abilitylookup" al on ab.abilityname = al.abilityname
                                    #             where al.abilityindex = {int.from_bytes(c.read_memory(abildatapoint,1))} and ga.generationid <= {gen}
                                    #         order by ga.generationid desc
                                    #         """
                                    #     abilityname2,abilitydescription2 = cursor.execute(query).fetchone()
                                    #     if abilityname2==pkmn.ability['name']:
                                    #         if abilityname2 not in abblist:
                                    #             print(int.from_bytes(c.read_memory(136334160-714472,1))) #xy oras:135669536
                                    #             window['-ability-e-'].Update(str(pkmn.ability['name']), text_color="#f0f080")
                                    #             window['-ability-e-'].set_tooltip(str(pkmn.ability['description']))
                                    #             if pkmn.abilityname not in trackdata[pkmn.name]['abilities']:
                                    #                 trackdata[pkmn.name]['abilities'].append(pkmn.abilityname)
                                    #     elif change == 'abil':
                                    #         window['-ability-e-'].set_tooltip('')
                                    #     if gen == 7: # need the legacy code for gen 7
                                    #         startupabils=["Air Lock","Cloud Nine","Delta Stream","Desolate Land","Download","Drizzle","Drought","Forewarn","Imposter","Intimidate","Mold Breaker","Pressure","Primordial Sea","Sand Stream","Slow Start","Snow Warning","Teravolt","Turboblaze","Trace","Unnerve","Aura Break","Fairy Aura","Dark Aura",'Psychic Surge','Electric Surge','Misty Surge','Grassy Surge','Comatose']
                                    #         if abilityname in startupabils:
                                    #             window['-ability-e-'].Update(str(pkmn.ability['name']), text_color="#f0f080")
                                    #             window['-ability-e-'].set_tooltip(str(pkmn.ability['description']))
                                    #             if pkmn.abilityname not in trackdata[pkmn.name]['abilities']:
                                    #                 trackdata[pkmn.name]['abilities'].append(pkmn.abilityname)
                                    #         elif change == 'abil':
                                    #             window['-ability-e-'].set_tooltip('')
                                    #         else:
                                    #             window['-ability-e-'].Update('Unknown Ability', text_color="#f0f080")
                                    # except:
                                    #     window['-ability-e-'].Update('Unknown Ability', text_color="#f0f080")

                                    if pkmn.level not in trackdata[pkmn.name]['levels']:
                                        trackdata[pkmn.name]['levels'].append(pkmn.level)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    # show enemy stuff in battle
                                    window['-tc1a-e-'].Update(visible = True)
                                    window['-tc2-e-'].update(visible = True)
                                    window['-bc1a-e-'].Update(visible = True)
                                    window['-bc2a-e-'].Update(visible = True)
                                    # window['-bc3a-e-'].Update(visible = False)
                                    window['-bc4a-e-'].Update(visible = True)
                                    window['-bc5a-e-'].Update(visible = True)
                                    window['-bc6a-e-'].Update(visible = True)
                                    window['-bc7a-e-'].Update(visible = True)
                                    # update enemy slot info
                                    try:
                                        window['-monimg-e-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                    except:
                                        window['-monimg-e-'].Update(visible = False)
                                        print(Exception)
                                    window['-monname-e-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                    window['-monnum-e-'].Update(f'#{str(pkmn.species_num())}')
                                    window['-level-e-'].Update(f'Level: {enemylevel} (Seen {len(trackdata[pkmn.name]["levels"])})')
                                    window['-level-e-'].set_tooltip(f'Seen at {trackdata[pkmn.name]["levels"]}')
                                    window['-note-e-'].update(trackdata[pkmn.name]["notes"])
                                    window['-note-e-'].set_tooltip(trackdata[pkmn.name]["notes"])
                                    for i in range(0, 6):
                                        j = ['hp', 'att', 'def', 'spatt', 'spdef', 'speed']
                                        if trackdata[pkmn.name]['stats'][i] == '+':
                                            col = '#80f080'
                                        elif trackdata[pkmn.name]['stats'][i] == '-':
                                            col = '#f08080'
                                        else:
                                            col = '#ffffff'
                                        window[f'-{j[i]}-e-'].update(f'[{trackdata[pkmn.name]['stats'][i]}]', text_color = col)
                                    
                                    window['-bst-e-'].Update(pkmn.bst)

                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-20),1)) <= 12:
                                        window['-attmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-20),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-19),1)) <= 12:
                                        window['-defmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-19),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-18),1)) <= 12:
                                        window['-spattmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-18),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-17),1)) <= 12:
                                        window['-spdefmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-17),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-16),1)) <= 12:
                                        window['-speedmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-16),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-15),1)) <= 12:
                                        window['-accmod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-15),1))), visible = True)
                                    if 0 <= int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-14),1)) <= 12:
                                        window['-evamod-e-'].Update('images/modifiers/modifier{}.png'.format(int.from_bytes(c.read_memory((ppadd+(mongap*(pk-1))-14),1))), visible = True)
                                    
                                    window['-movehdr-e-'].update(f'Moves {learnedcount}/{totallearn} ({nmove})')
                                    window['-movehdr-e-'].set_tooltip(learnstr)
                                    window['-movepphdr-e-'].update('PP')
                                    window['-movebphdr-e-'].update('Pow')
                                    window['-moveacchdr-e-'].update('Acc')
                                    window['-movecontacthdr-e-'].update('C')
                                    window['-prevmoves-e-'].update('Previous Moves: ' + re.sub('[^A-Za-z0-9 ]+', '', str(trackdata[pkmn.name]['moves'])))
                                    window['-abillist-e-'].update('Known Abilities: ' + re.sub('[^A-Za-z0-9, ]+', '', str(trackdata[pkmn.name]['abilities'])))
                                    ### STATS ########
                                    ### MOVES ########
                                    totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                    # counts = pkmn.getCoverage(gen,gamegroupid)
                                    if pkmn.level not in trackdata[pkmn.name]['levels']:
                                        trackdata[pkmn.name]['levels'].append(pkmn.level)
                                    nmove = (' - ' if not nextmove else nextmove)
                                    movect = 0
                                    for move in pkmn.moves:
                                        if int.from_bytes(c.read_memory(ppadd+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1))==int.from_bytes(c.read_memory(ppadd+1+(mongap*(pk-1))+(14*(pkmn.moves).index(move)),1)): 
                                            continue
                                        # typetable={
                                        #     "Normal":[1,1,1,1,1,.5,1,0,.5,1,1,1,1,1,1,1,1,1,1],
                                        #     "Fighting":[2,1,.5,.5,1,2,.5,0,2,1,1,1,1,.5,2,1,2,.5,1],
                                        #     "Flying":[1,2,1,1,1,.5,2,1,.5,1,1,2,.5,1,1,1,1,1,1],
                                        #     "Poison":[1,1,1,.5,.5,.5,1,.5,0,1,1,2,1,1,1,1,1,2,1],
                                        #     "Ground":[1,1,0,2,1,2,.5,1,2,2,1,.5,2,1,1,1,1,1,1],
                                        #     "Rock":[1,.5,2,1,.5,1,2,1,.5,2,1,1,1,1,2,1,1,1,1],
                                        #     "Bug":[1,.5,.5,.5,1,1,1,.5,.5,.5,1,2,1,2,1,1,2,.5,1],
                                        #     "Ghost":[0,1,1,1,1,1,1,2,1,1,1,1,1,2,1,1,.5,1,1],
                                        #     "Steel":[1,1,1,1,1,2,1,1,.5,.5,.5,1,.5,1,2,1,1,2,1],
                                        #     "Fire":[1,1,1,1,1,.5,2,1,2,.5,.5,2,1,1,2,.5,1,1,1],
                                        #     "Water":[1,1,1,1,2,2,1,1,1,2,.5,.5,1,1,1,.5,1,1,1],
                                        #     "Grass":[1,1,.5,.5,2,2,.5,1,.5,.5,2,.5,1,1,1,.5,1,1,1],
                                        #     "Electric":[1,1,2,1,0,1,1,1,1,1,2,.5,.5,1,1,.5,1,1,1],
                                        #     "Psychic":[1,2,1,2,1,1,1,1,.5,1,1,1,1,.5,1,1,0,1,1],
                                        #     "Ice":[1,1,2,1,2,1,1,1,.5,.5,.5,2,1,1,.5,2,1,1,1],
                                        #     "Dragon":[1,1,1,1,1,1,1,1,.5,1,1,1,1,1,1,2,1,0,1],
                                        #     "Dark":[1,.5,1,1,1,1,1,2,1,1,1,1,1,2,1,1,.5,.5,1],
                                        #     "Fairy":[1,2,1,.5,1,1,1,1,.5,.5,1,1,1,1,1,2,2,1,1],
                                        #     "Null":[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
                                        #     "-":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                                        # }
                                        # typedic={"Normal":0,"Fighting":1,"Flying":2,"Poison":3,"Ground":4,"Rock":5,"Bug":6,"Ghost":7,"Steel":8,"Fire":9,"Water":10,"Grass":11,"Electric":12,"Psychic":13,"Ice":14,"Dragon":15,"Dark":16,"Fairy":17,"Null":18}

                                        # print(currmon.types)
                                        # if movetyp!=None:
                                        #     for type in currmon.types:
                                        #         typemult=typemult*(typetable[movetyp][typedic[type]])
                                        # modimage="6"
                                        # if move["category"]!="Non-Damaging":
                                        #     if typemult==.25:
                                        #         modimage="4"
                                        #     elif typemult==.5:
                                        #         modimage="5"
                                        #     # elif typemult==1:
                                        #     #     modimage="6"
                                        #     elif typemult==2:
                                        #         modimage="7"
                                        #     elif typemult==4:
                                        #         modimage="8"
                                        #     elif typemult==0:
                                        #         modimage="X"
                                        stab = ''
                                        for type in pkmn.types:
                                            if move['type'] == type[0]:
                                                stab = move['type']
                                                continue
                                        movepower = calcPower(pkmn,move,1,1,0,0)
                                        # acc = '-' if not move['acc'] else int(move['acc'])
                                        acc = calcAcc(move, enemylevel, slotlevel)
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
                                    evofriend = ''
                                    evolevel = ''
                                    evostring = ''
                                    evoloc = ''
                                    if pkmn.name == 'Eevee':
                                        evoitem = 'Any stone'
                                    elif pkmn.name == 'Gloom':
                                        evoitem = 'Leaf Stone/Sun Stone'
                                    elif pkmn.name == 'Poliwhirl':
                                        evoitem = 'Water Stone/Kings Rock'
                                    elif pkmn.name == 'Clamperl':
                                        evoitem = 'Deep Sea Tooth/Deep Sea Scale'
                                    elif pkmn.name == 'Slowpoke':
                                        evoitem = 'Kings Rock/Level 37'
                                    elif pkmn.name == 'Kirlia':
                                        evoitem = 'Lvl 30/Dawn Stone (M)'
                                    # need to check snorunt
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
                                if pkmn.status != '':
                                    window['-status-'].Update(resize('images/statuses/{}.png'.format(pkmn.status), (75, 20)), visible = True)
                                else:
                                    window['-status-'].Update(visible = False)
                                ### MOVES ########
                                totallearn,nextmove,learnedcount,learnstr = pkmn.getMoves(gamegroupid)
                                nmove = (' - ' if not nextmove else nextmove)
                                ### UPDATING TRACKER INFO ###
                                # print(slot)
                                attackchange,defchange,spatkchange,spdefchange,speedchange = pkmn.getStatChanges()
                                naturelist = [attackchange,defchange,spatkchange,spdefchange,speedchange]
                                confuseberry, confusestat = natureberries(naturelist)
                                query=f"""select
                                        itemname
                                        ,itemdesc
                                    from "generationitem" 
                                    where itemname = '{pkmn.held_item_name}' and genid <= {gen}
                                    """
                                itemname,itemdesc = cursor.execute(query).fetchone()
                                itemname=itemname.encode("utf-8").decode("utf-8")
                                window['-ph1-'].update('', visible = False)
                                window['-slot-'].update(f'Seed {seed} ({gameabbr})')
                                try:
                                    window['-monimg-'].Update(resize('images/homemodels/{}.png'.format(pkmn.name), (120,120)), visible = True)
                                except:
                                    window['-monimg-'].Update(visible = False)
                                    print(Exception)
                                window['-monname-'].Update(pkmn.name.replace("Farfetchd","Farfetch'd"))
                                window['-monnum-'].Update('#{}'.format(str(pkmn.species_num())))
                                window['-level-'].Update('Level: {}'.format(str(pkmn.level)))
                                # window['-level-'].set_tooltip('Seen at {}'.format(trackdata[pkmn.name]["levels"]))
                                window['-tc2-'].update(visible = True)
                                window['-tc2b-'].update(visible = True)
                                window['-tc3-'].update(visible = True)
                                window['-bc1-'].update(visible = True)
                                window['-bc2-'].update(visible = True)
                                window['-bc4-'].update(visible = True)
                                window['-bc5-'].update(visible = True)
                                window['-bc6-'].update(visible = True)
                                window['-ability-'].update(str(pkmn.ability['name']), text_color="#f0f080")
                                window['-ability-'].set_tooltip(str(pkmn.ability['description']))
                                window['-item-'].update(pkmn.held_item_name)
                                window['-item-'].set_tooltip(itemdesc)
                                if gen == 6:
                                    window['-hpheals-'].update("Heals: "+str(hphl["percent"])+"% ("+str(hphl["total"])+")", visible = True, text_color="#f0f080")
                                    window['-hpheals-'].set_tooltip(f'Click to view in new window. \n' +
                                        f'HP Heals: {str(hphl).replace("'", '').replace('{', '').replace('}', '').title()}\n'+
                                        f'Status Heals: {str(statushl).replace("'", '').replace('{', '').replace('}', '').title()}\n'+
                                        f'PP Heals: {str(pphl).replace("'", '').replace('{', '').replace('}', '').title()}')
                                else: # don't currently have support for gen 7 :<
                                    window['-hpheals-'].update(visible = False)
                                window['-hplabel-'].update(visible = True)
                                window['-attlabel-'].update(visible = True, text_color=natureformatting(naturelist, 0))
                                window['-deflabel-'].update(visible = True, text_color=natureformatting(naturelist, 1))
                                window['-spattlabel-'].update(visible = True, text_color=natureformatting(naturelist, 2))
                                window['-spdeflabel-'].update(visible = True, text_color=natureformatting(naturelist, 3))
                                window['-speedlabel-'].update(visible = True, text_color=natureformatting(naturelist, 4))
                                window[confusestat].set_tooltip('{} causes confusion'.format(confuseberry))
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
                                window['-accevalabel-'].update(visible = False)
                                window['-accmod-'].update('images/modifiers/modifier6.png')
                                window['-accevaph-'].update(visible = False)
                                window['-evamod-'].update('images/modifiers/modifier6.png')
                                window['-movehdr-'].update('Moves {}/{} ({})'.format(learnedcount, totallearn, nmove))
                                window['-movehdr-'].set_tooltip(learnstr)
                                window['-movepphdr-'].update('PP')
                                window['-movebphdr-'].update('Pow')
                                window['-moveacchdr-'].update('Acc')
                                window['-movecontacthdr-'].update('C')
                                if layout_logview != [[]]:
                                    window['-clearnotes-'].update(visible=True)
                                    window['-view-log-'].update(visible=True)
                                else: 
                                    window['-clearnotes-solo-'].update(visible=True)
                                window['-load-log-'].update(visible=True)
                                window['-settings-'].update(visible=True)                                
                                for move in pkmn.moves:
                                    stab = ''
                                    movetyp=movetype(pkmn,move,pkmn.held_item_num)
                                    for type in pkmn.types:
                                        if move['type'] == type[0]:
                                            stab = move['type']
                                            # print(stab)
                                            continue
                                    movepower = calcPower(pkmn,move,pkmn.cur_hp,pkmn.maxhp,0,0)
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
                                window['-tc2-e-'].update(visible = False)
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
        time.sleep(5)
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

with open('data/item-data.json','r', encoding="utf-8") as f:
    items = json.loads(f.read())

if __name__ == "__main__" :
    run()

exit()
