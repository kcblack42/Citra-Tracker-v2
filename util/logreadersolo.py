import FreeSimpleGUI as sg
import json
import pathlib
import pandas as pd
import re
import io

# track_size = (380, 580)
# font_sizes = [14, 12, 10, 15]
# sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=150)
# pokemonnum = 0
# log = open('seed_XY.log', encoding="utf8").read()

def logloader_solo(track_size):
    f = sg.PopupGetFile('Select log file.', title='Log Loader')
    print(f)
    log = open(f, encoding="utf8").read()
    pokemonnum = 0
    pkmn_srch = 0

    def set_size(element, size):
        # Only work for sg.Column when `scrollable=True` or `size not (None, None)`
        options = {'width':size[0], 'height':size[1]}
        if element.Scrollable or element.Size!=(None, None):
            element.Widget.canvas.configure(**options)
        else:
            element.Widget.pack_propagate(0)
            element.set_size(size)

    # def layout_logview(pokemonnum, log):
    log.count('\n--')
    lsplit = log.split('\n--')

    if (lsplit[-3].count('Pokemon X') >= 1) | (lsplit[-3].count('Pokemon Y') >= 1):
        game = 'XY'
    elif (lsplit[-3].count('Pokemon Omega') >= 1) | (lsplit[-3].count('Pokemon Alpha') >= 1):
        game = 'ORAS'
    elif (lsplit[-3].count('Pokemon Sun') >= 1) | (lsplit[-3].count('Pokemon Moon') >= 1):
        game = 'SM'
    elif (lsplit[-3].count('Pokemon Ultra') >= 1):
        game = 'USUM'
    else:
        game = 'UNK'

    if game != 'UNK':
        print(f'Log from Pokemon {game}.')
    else:
        print('Error reading log.')

    if game in ('XY', 'ORAS'):
        gen = 6
    elif game in ('SM', 'USUM'):
        gen = 7

    for i in lsplit:
        if i.startswith('Randomized Evolutions'):
            evos = i
        elif i.startswith('Pokemon Base Stats & Types'):
            mons = i
        elif i.startswith('Pokemon Movesets'):
            moves = i
        elif i.startswith('TM Moves'):
            tms = i
        elif i.startswith('TM Compatibility'):
            tmcompat = i
        elif i.startswith('Trainers Pokemon'):
            trainer = i
        elif i.startswith('Wild Pokemon'):
            wildmons = i
        elif i.startswith('Totem Pokemon'):
            totems = i
        elif i.startswith('Move Tutor Moves'):
            tutormoves = i
        elif i.startswith('Move Tutor Compatibility'):
            tutorcompat = i

    def parser(data, pattern, s):
        groups = [m.groupdict() for line in data.split(sep=s) if (m := re.match(pattern, line))]
        return groups

    # evolutions
    # evos_regex = r'(?P<preevo>\S+)+\s+(?P<postevo>\S+)?'
    # evos_df = pd.DataFrame(parser(evos.replace('->', ''), evos_regex, '\n')[1:])
    evos_df = pd.DataFrame([l for l in evos.split(sep='\n')][1:-1])
    evos_df[['preevo', 'postevo']] = evos_df[0].str.split('->', expand=True)
    evos_df['postevo'] = evos_df['postevo'].str.replace(' and ',';')
    evos_df['postevo'] = evos_df['postevo'].str.replace(', ',';')
    evos_df = evos_df.drop(columns=0)
    evos_df['preevo'] = evos_df['preevo'].str.strip()
    evos_df['postevo'] = evos_df['postevo'].str.strip()

    # mons
    mons_df = pd.read_csv(io.StringIO(mons.replace('Pokemon Base Stats & Types--','')), sep='|')
    mons_df.columns = mons_df.columns.str.strip()
    mons_df[mons_df.select_dtypes('object').columns] = mons_df[mons_df.select_dtypes('object').columns].apply(lambda x: x.str.strip())
    mons_df[['TYPE1', 'TYPE2']] = mons_df['TYPE'].str.split('/', expand=True)

    # tm compatibility
    tmcompat_df = pd.read_csv(io.StringIO(tmcompat.replace('TM Compatibility--','')), sep='|', header=None)
    tmcompat_df[['NUM', 'NAME']] = tmcompat_df[0].str.strip().str.split(' ', n=1, expand=True)
    tmcompat_df = tmcompat_df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # moves
    moves_df = moves.replace('Pokemon Movesets--\n', '').split('\n\n')
    moves_df = pd.DataFrame(moves_df).rename(columns={0:'mon'})
    moves_df = moves_df.apply(lambda x: x['mon'].split('\n'), axis=1)
    moves_df = pd.DataFrame(moves_df.values.tolist()).add_prefix('col_')
    moves_df.drop(columns=moves_df.columns[1:7], inplace=True)
    moves_regex = r"(?P<num>\d+)+\s+(?P<mon>\S+)+\s[->]+\s+(?P<evo>.+)?"
    moves_label = moves_df['col_0'].str.extract(moves_regex)
    moves_df = pd.concat([moves_label, moves_df], axis=1).drop(columns='col_0')
    moves_df.iloc[:, 3:] = moves_df.iloc[:, 3:].where(moves_df.iloc[:, 3:].apply(lambda x: x.str.startswith('Level')))
    moves_df['evo'] = moves_df['evo'].replace('(no evolution)', '')
    moves_df.dropna(axis=1, how='all', inplace=True)

    # tms
    tm_regex = r"(?P<tmnum>\w+)+\s+(?P<move>.*)"
    tms_df = pd.DataFrame(parser(tms, tm_regex, '\n')[1:])
    tms_df['tmnum'] = tms_df['tmnum'].str.replace('TM', '').astype(int)

    # trainers
    trainer_df = pd.DataFrame(trainer.replace('Trainers Pokemon--\n', '').split('\n'))
    trainer_df[['trainer', 'team']] = trainer_df[0].str.split(' - ', expand=True)
    trainer_df = trainer_df.drop(columns=0)
    trainer_df[['trainernum', 'trainername']] = trainer_df['trainer'].str.split(' \\(', expand=True, n=1)
    trainer_df[['trainerorig', 'trainerrename']] = trainer_df['trainername'].str.split('=>', expand=True, n=1)
    trainer_df = trainer_df.drop(columns=['trainer', 'trainerrename', 'trainername'])
    trainer_team = trainer_df['team'].str.split(',', expand=True)
    for (index, colname) in enumerate(trainer_team):
        new_col1 = 'pkmn_' + str(colname + 1)
        new_col2 = 'lvl_' + str(colname + 1)
        trainer_team[[new_col1, new_col2]] = trainer_team[colname].str.split(' Lv', expand=True)
        trainer_team.drop(columns=colname, inplace=True)
    trainer_df = pd.concat([trainer_df, trainer_team], axis=1).drop(columns='team')
    trainer_df = trainer_df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # wilds
    if gen == 6: #may need to be by game rather than by gen but we're starting here
        wilds_df = pd.DataFrame(wildmons.replace('Wild Pokemon--\n', '').split('\n\n')).rename(columns={0:'set'})
        wilds_df = wilds_df['set'].str.split('\n', expand=True)
        wilds_df[['set', 'loc']] = wilds_df[0].str.split('-', expand=True)
        wilds_df = wilds_df.drop(columns=0)
        for (index, colname) in enumerate(wilds_df.iloc[:, 0:12]):
            new_col1 = 'pkmn_' + str(colname)
            new_col2 = 'lvl_' + str(colname)
            wilds_df[colname] = wilds_df[colname].str[0:24].str.strip()
            wilds_df[[new_col1, new_col2]] = wilds_df[colname].str.split(' Lv', expand=True)
            wilds_df = wilds_df.drop(columns=colname)
    elif gen == 7:
        wilds_df = pd.DataFrame(wildmons.replace('Wild Pokemon--\n', '').split('\n\n')).rename(columns={0:'set'})
        wilds_df = wilds_df['set'].str.split('\n', expand=True)
        wilds_df = wilds_df.map(lambda x: None if str(x).__contains__('SOS') else x)
        wilds_df = wilds_df.dropna(axis=1, how='all')
        wilds_df.columns = list(range(0,11)) # renaming the lists now that we've gotten rid of the SOS cols
        wilds_df[['set', 'loc']] = wilds_df[0].str.split(' - ', expand=True)
        wilds_df = wilds_df.map(lambda x: str(x).replace('Lvs', 'Lv'))
        wilds_df = wilds_df.drop(columns=0)
        for (index, colname) in enumerate(wilds_df.iloc[:, 0:10]):
            new_col1 = 'pkmn_' + str(colname)
            new_col2 = 'lvl_' + str(colname)
            wilds_df[colname] = wilds_df[colname].str[0:29].str.strip()
            wilds_df[[new_col1, new_col2]] = wilds_df[colname].str.split(' Lv', expand=True)
            wilds_df = wilds_df.drop(columns=colname)
    wilds_df = wilds_df.map(lambda x: x.strip() if isinstance(x, str) else x)

    # joins for easier event handling later
    pokemon = pd.merge(mons_df, evos_df, how = 'left', left_on='NAME', right_on='preevo').drop(columns='preevo').rename(columns={'postevo':'EVOLUTION'})
    pokemon = pd.merge(pokemon, moves_df, how='left', left_on='NAME', right_on='mon').drop(columns=['num', 'mon', 'evo'])
    pokemon.columns = pokemon.columns.str.replace('col_', 'move_')
    pokemon['EVOLUTION'] = pokemon['EVOLUTION'].fillna('')
    pokemon = pokemon.sort_values('NAME')


    # charting stats
    def statchart(mon):
        base = 50
        i = 0
        stat = ['HP', 'ATK', 'DEF', 'SATK', 'SDEF', 'SPD']
        for s in mon[3:9]:
            x1 = 70 + (40 * i)
            y1 = base
            x2 = 100 + (40 * i)
            y2 = base + (s * .5)
            if s >= 180:
                graph.draw_rectangle((x1,y1), (x2,y2), line_color='green', fill_color='green')
            elif s <= 40:
                graph.draw_rectangle((x1,y1), (x2,y2), line_color='red', fill_color='red')
            else:
                graph.draw_rectangle((x1,y1), (x2,y2), line_color='white', fill_color='white')
            graph.DrawText(stat[i], location=((x1 + x2)/2, base-2), color='white', text_location=sg.TEXT_LOCATION_TOP, font=('Franklin Gothic Medium', 12))
            graph.DrawText(s, location=((x1 + x2)/2, y2+2), color='white', text_location=sg.TEXT_LOCATION_BOTTOM, font=('Franklin Gothic Medium', 12))
            i += 1

        graph.DrawText(f'{mon.iloc[1]} ({sum(mon.iloc[3:9])} BST)', location=(70, base+180), color='#f0f080', text_location=sg.TEXT_LOCATION_TOP_LEFT, font=('Franklin Gothic Medium', 16))
        graph.DrawLine(point_from=(65,base), point_to=(305,base), color='white')


    def movelist(mon, logmoves = [], mvlist = []):
        mon = mon.to_list()
        i = 0
        logmoves = []
        logmoves.append([sg.Text(f'Moveset:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
        mvlist = []
        while i < len(mon):
            if str(mon[i]) != 'nan':
                mon[i] = str(mon[i]).replace('Level ', '')
                logmoves.append([sg.Text(mon[i], text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-', visible = True, pad=(0,0,0,0))])
                mvlist.append(mon[i])
            else:
                logmoves.append([sg.Text('', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-', pad=(0,0,0,0))])
            i += 1
        return logmoves, mvlist


    def abillist(mon):
        alist = mon[['ABILITY1', 'ABILITY2', 'ABILITY3']]
        logabils = []
        logabils.append([sg.Text(f'Abilities:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
        i = 0
        while i < len(alist):
            if i == 2:
                logabils.append([sg.Text(f'{alist.iloc[i]} (HA)', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-al{i}-', visible = True)])
            else:
                logabils.append([sg.Text(alist.iloc[i], text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-al{i}-', visible = True)])
            i += 1
        return logabils, alist


    def evolist(mon):
        logevos = []
        elist = mon['EVOLUTION']
        logevos.append([sg.Text(f'Evolutions:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
        if elist == '':
            logevos.append([sg.Text(f'None', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
            elist = 'None'
        elif elist.count(';') in (1, 2):
            elist = elist.replace(';', '\n')
            logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
        elif elist.count(';') > 2:
            i = 0
            x = elist.count(';')
            while i < x:
                elist = elist.replace(';', ', ', 1)
                elist = elist.replace(';', ',\n', 1)
                i += 2
            logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-evos-', visible = True)])
        else:
            logevos.append([sg.Text(f'{elist}', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-evos-', visible = True)])
        return logevos, elist

    def tmlist(mon, game, tmcompat_df, tms_df):
        logtms1, logtms4, logtmsfull, tmtext, tmtextfull = [], [], [], [], []
        tmdict, tmdictfull = {}, {}
        if game == 'XY':
            gymtmlist = [83, 39, 98, 86, 24, 99, 4, 13]
        elif game == 'ORAS':
            gymtmlist = [39, 8, 72, 50, 67, 19, 4, 31] #TM31 is 
        elif game == 'SM':
            gymtmlist = [4, 13, 24, 39, 83, 86, 98, 99]
        elif game == 'USUM':
            gymtmlist = [1, 19, 54, 43, 67, 29, 66]
        logtms1.append([sg.Text(f'Leader TMs:', text_color='#f0f080', font=('Franklin Gothic Medium', 14), visible = True)])
        i,j = 0,0
        while i < len(gymtmlist):
            if tmcompat_df.iloc[mon.iloc[0]-1, gymtmlist[i]] == '-':
                logtms1.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm1{i}-', visible = True)])
                logtms4.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm4{i}-', visible = True)])
                tmdict[f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}'] = False
            else:
                logtms1.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='#339ec4', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm1{i}-', visible = True)])
                logtms4.append([sg.Text(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}', text_color='#339ec4', font=('Franklin Gothic Medium', 10), key = f'-log-gymtm4{i}-', visible = True)])
                tmdict[f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}'] = True
            tmtext.append(f'TM{tms_df['tmnum'][gymtmlist[i]-1]} {tms_df['move'][gymtmlist[i]-1]}')
            i += 1
        while j < 100: # 100 TMs in both gens 6 and 7, there are HMs in the list so need to use flat number
            if tmcompat_df.iloc[mon.iloc[0]-1, j + 1] == '-':
                logtmsfull.append([sg.Text(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}', text_color='white', font=('Franklin Gothic Medium', 10), key = f'-log-fulltm{j}-', visible = True)])
                tmdictfull[f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}'] = False
            else:
                logtmsfull.append([sg.Text(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}', text_color='#339ec4', font=('Franklin Gothic Medium', 10), key = f'-log-fulltm{j}-', visible = True)])
                tmdictfull[f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}'] = True
            tmtextfull.append(f'TM{tms_df['tmnum'][j]} {tms_df['move'][j]}')
            j += 1
        return logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull

    def pivotlist(game):
        logpivotlocs, logpivotbase1, logpivotbase2, sorter = [], [], [], []
        pivottext = {}
        # print(game)
        if game == 'XY':
            sets = ['Set #22', 'Set #138', 'Set #23', 'Set #132', 'Set #36', 'Set #37', 'Set #38', 'Set #223', 'Set #42', 'Set #43', 'Set #45', 'Set #6', 'Set #52']
            locs = ['Route 2', 'Santalune Forest', 'Route 3', 'Route 22', 'Route 7 (Grass)', 'Route 7 (Yellow)', 'Route 7 (Purple)', 'Connecting Cave', 'Route 8 (Grass)', 'Route 8 (Yellow)', 'Route 8 (Rock)', 'Ambrette Town (Rock)', 'Route 9']
        elif game == 'ORAS':
            sets = ['Set #34', 'Set #39', 'Set #48', 'Set #66', 'Set #346', 'Set #57', 'Set #42', 'Set #51', 'Set #69', 'Set #60', 'Set #147', 'Set #2', 'Set #10']
            locs = ['Route 101', 'Route 102', 'Route 103', 'Route 104 (South)', 'Petalburg Woods', 'Route 104 (North)', 'Route 102 (Old Rod)', 'Route 103 (OR)', 'Route 104 (South, OR)', 'Route 104 (North, OR)', 'Route 115 (OR)', 'Dewford Town (OR)', 'Petalburg City (OR)']
        elif gen == 7:
            sets = ['Set #1', 'Set #2', 'Set #12', 'Set #13', 'Set #14', 'Set #3', 'Set #10', 'Set #80', 'Set #81', 'Set #82', 'Set #83', 'Set #29', 'Set #31', 'Set #28', 'Set #30', 'Set #49', 'Set #53', 'Set #52', 'Set #54', 'Set #56', 'Set #57', 'Set #68', 'Set #69', 'Set #34', 'Set #43', 'Set #47', 'Set #70', 'Set #71']
            locs = ['Route 1 Grass #1', 'Route 1 Grass #2', 'Route 1 Grass #3', 'Route 1 Grass #4', 'Route 1 Grass #5', "Professor's House #1", "Professor's House #2", 'Trainers School #1', 'Trainers School #2', 'Trainers School #3', 'Trainers School #4', 'Hauoli Grass Area #1', 'Hauoli Grass Area #2', 'Hauoli Grass Area #3', 'Hauoli Grass Area #4', 'Route 2 Grass #1', 'Route 2 Grass #2', 'Route 2 Grass #3', 'Route 2 Grass #4', 'Route 2 Grass #5', 'Route 2 Grass #6', 'Hauoli Cemetary #1', 'Hauoli Cemetary #2', 'Route 3 Grass #1', 'Route 3 Grass #2', 'Route 3 Grass #3', 'Melemele Meadow', 'Seaward Cave']
        for i in range(0, len(sets)):
            sorter.append(i)
        # pivotlocs = pd.merge(wilds_df, pd.DataFrame(sets, locs).reset_index(), how = 'inner', left_on='set', right_on=0).rename(columns={'index':'locname'})
        pivotdf = pd.DataFrame([sets, locs, sorter]).transpose()
        pivotlocs = pd.merge(wilds_df, pivotdf, how = 'inner', left_on='set', right_on=0).rename(columns={1:'locname'})
        pivotlocs = pivotlocs.infer_objects(copy=False).fillna('')
        pivotlocs = pivotlocs.sort_values(2).reset_index()

        f1 = ('Franklin Gothic Medium', 12)
        f2 = ('Franklin Gothic Medium', 10)
        logpivotlocs.append([sg.Text(f'Locations:', text_color='#f0f080', font=f1, visible = True)])
        logpivotbase1.append([sg.Text(f'Pokemon', text_color='#f0f080', font=f1, visible = True)])
        logpivotbase2.append([sg.Text(f'Level', text_color='#f0f080', font=f1, visible = True)])

        for i in range(0, len(pivotlocs)):
            logpivotlocs.append([sg.Text(f'{pivotlocs['locname'][i]}', text_color='white', font=f2, key = f'-logpivot-loc{i}-', visible = True, enable_events=True)])
            j = 1
            if gen == 6:
                while j <= 12: # 12 encounter slots in gen 6
                    if i == 0:
                        logpivotbase1.append([sg.Text('', text_color='white', font=f2, key = f'-logpivot-mon{j}-', visible = True, justification='c')])
                        logpivotbase2.append([sg.Text('', text_color='white', font=f2, key = f'-logpivot-lvl{j}-', visible = True, justification='c')])
                    pivottext[f'{i}-{j}'] = [f'{pivotlocs[f'pkmn_{j}'][i]}', f'{pivotlocs[f'lvl_{j}'][i]}']
                    j += 1
            elif gen == 7: 
                while j <= 10: # 10 encounter slots in gen 7
                    if i == 0:
                        logpivotbase1.append([sg.Text('', text_color='white', font=f2, key = f'-logpivot-mon{j}-', visible = True, justification='c')])
                        logpivotbase2.append([sg.Text('', text_color='white', font=f2, key = f'-logpivot-lvl{j}-', visible = True, justification='c')])
                    pivottext[f'{i}-{j}'] = [f'{pivotlocs[f'pkmn_{j}'][i]}', f'{pivotlocs[f'lvl_{j}'][i]}']
                    j += 1
        return logpivotlocs, logpivotbase1, logpivotbase2, pivottext

    def trainerlist(game):
        log_tlist, log_tparty1, log_tparty2, log_tparty3 = [], [], [], []
        tfont = ('Franklin Gothic Medium', 12)
        tfont2 = ('Franklin Gothic Medium', 10)
        if game == 'XY':
            name = ['Viola', 'Grant', 'Korrina', 'Ramos', 'Clemont', 'Valerie', 'Olympia', 'Wulfric', 'E4 Wikstrom', 'E4 Malva', 'E4 Drasna', 'E4 Siebold', 'Diantha', 'Lysandre #1', 'Lysandre #2', 'Lysandre #3']
            idx = [5, 75, 20, 21, 22, 23, 24, 25, 186, 268, 269, 270, 275, 302, 524, 525]
            titles = ['Rivals', 'Gym Leaders', 'Elite Four', 'Team Flare']
            t_dict = {titles[0]:'', 
                titles[1]:{name[0]:[idx[0]], name[1]:[idx[1]], name[2]:[idx[2]], name[3]:[idx[3]], name[4]:[idx[4]], name[5]:[idx[5]], name[6]:[idx[6]], name[7]:[idx[7]]}, 
                titles[2]:{name[8]:[idx[8]], name[9]:[idx[9]], name[10]:[idx[10]], name[11]:[idx[11]], name[12]:[idx[12]]},
                titles[3]:{name[13]:[idx[13]], name[14]:[idx[14]], name[15]:[idx[15]]}}
        elif game == 'ORAS':
            name = ['Wally', 'Roxanne', 'Brawly', 'Wattson', 'Flannery', 'Norman', 'Winona', 'Tate & Liza', 'Wallace', 'E4 Sidney', 'E4 Phoebe', 'E4 Glacia', 'E4 Drake', 'Steven', 'Archie #1', 'Archie #2', 'Maxie #1', 'Maxie #2']
            idx = [560, 562, 566, 568, 569, 570, 551, 571, 552, 553, 554, 555, 556, 582, 230, 177, 235, 234]
            titles = ['Rivals', 'Gym Leaders', 'Elite Four', 'Magma/Aqua']
            t_dict = {titles[0]:{name[0]:[idx[0]]}, 
                titles[1]:{name[1]:[idx[1]], name[2]:[idx[2]], name[3]:[idx[3]], name[4]:[idx[4]], name[5]:[idx[5]], name[6]:[idx[6]], name[7]:[idx[7]], name[8]:[idx[8]]}, 
                titles[2]:{name[9]:[idx[9]], name[10]:[idx[10]], name[11]:[idx[11]], name[12]:[idx[12]], name[13]:[idx[13]]},
                titles[3]:{name[14]:[idx[14]], name[15]:[idx[15]], name[16]:[idx[16]], name[17]:[idx[17]]}}
        elif game == 'SM':
            name = ['Hala', 'Olivia', 'Nanu', 'Hapu', 'E4 Hala', 'E4 Olivia', 'E4 Acerola', 'E4 Kahili', 'Kukui v1', 'Kukui v2', 'Kukui v3', 'Guzma #1', 'Guzma #2', 'Guzma #3', 'Lusamine #1', 'Lusamine #2']
            idx = [22, 89, 153, 154, 151, 152, 148, 155, 128, 412, 413, 137, 234, 235, 130, 157]
            titles = ['Hau', 'Kahunas', 'Elite Four', 'Skull/Aether']
            t_dict = {titles[0]:'', 
                titles[1]:{name[0]:[idx[0]], name[1]:[idx[1]], name[2]:[idx[2]], name[3]:[idx[3]]}, 
                titles[2]:{name[4]:[idx[4]], name[5]:[idx[5]], name[6]:[idx[6]], name[7]:[idx[7]], name[8]:[idx[8]], name[9]:[idx[9]], name[10]:[idx[10]]},
                titles[3]:{name[11]:[idx[11]], name[12]:[idx[12]], name[13]:[idx[13]], name[14]:[idx[14]], name[15]:[idx[15]]}}
        elif game == 'USUM':
            name = ['Hala', 'Olivia', 'Nanu #1', 'Nanu #2', 'Hapu', 'E4 Molayne', 'E4 Olivia', 'E4 Acerola', 'E4 Kahili', 'Hau (Champ) v1', 'Hau (Champ) v2', 'Hau (Champ) v3', 'Guzma #1', 'Guzma #2', 'Guzma #3', 'Lusamine']
            idx = [22, 89, 153, 507, 496, 488, 152, 148, 155, 493, 494, 495, 137, 234, 235, 130]
            titles = ['Hau', 'Kahunas', 'Elite Four', 'Skull/Aether']
            t_dict = {titles[0]:'', 
                titles[1]:{name[0]:[idx[0]], name[1]:[idx[1]], name[2]:[idx[2]], name[3]:[idx[3]], name[4]:[idx[4]]}, 
                titles[2]:{name[5]:[idx[5]], name[6]:[idx[6]], name[7]:[idx[7]], name[8]:[idx[8]], name[9]:[idx[9]], name[10]:[idx[10]], name[11]:[idx[11]]},
                titles[3]:{name[12]:[idx[12]], name[13]:[idx[13]], name[14]:[idx[14]], name[15]:[idx[15]]}}
        # when dealing with mons, be careful with ones that have held items (it'll be [mon]@[item])
        r = r'(?P<mon>[^@]+)+\@+(?P<item>[^@]+)'
        for i in range(0, len(titles)):
            for j in range(0, len(idx)):
                if t_dict[titles[i]] == '':
                    continue
                elif name[j] in t_dict[titles[i]]:
                    t_dict[titles[i]][name[j]].append(trainer_df.iloc[idx[j], 2:].to_list())
                    z = 0
                    for k in t_dict[titles[i]][name[j]][1]:
                        if str(k).find('@') != -1:
                            t_dict[titles[i]][name[j]][1][z] = re.split(r, str(k))[1:3]
                        if z/2 == int(z/2): # need a length 6, will fill in the values in the event statements
                            y = int(z/2)
                            log_tparty1.append([sg.Text(f'', text_color='white', font=tfont2, key = f'-log-train-pkmnname-{y}-', visible = True, justification='c', enable_events=True)])
                            log_tparty2.append([sg.Text(f'', text_color='white', font=tfont2, key = f'-log-train-pkmnlvl-{y}-', visible = True, justification='c', enable_events=True)])
                            log_tparty3.append([sg.Text(f'', text_color='white', font=tfont2, key = f'-log-train-pkmnitem-{y}-', visible = True, justification='c', enable_events=True)])
                        z += 1
                    log_tlist.append([sg.Text(f'{name[j]}', text_color='white', font=tfont2, key = f'-log-train-{j}-', visible = True, justification='c', enable_events=True)])
        return t_dict, titles, log_tlist, log_tparty1, log_tparty2, log_tparty3, name

    t_dict, t_types, log_tlist, log_tparty1, log_tparty2, log_tparty3, t_names = trainerlist(game)
    # x = t_dict['Kahunas']['Olivia'][1]
    # str(x).split(r'(?P<mon>[^@]+)+\@+(?P<item>[^@]+)')


    def searchfcn(pokemon, p):
        pkmnnum = pokemon.loc[pokemon['NUM'] == (p + 1)].iloc[0,0]
        l = pokemon['NAME'].to_list()
        l.sort() # this one's what we use for the actual input box
        lcase = pokemon['NAME'].str.casefold().to_list() # allows case insensitivity
        searchpopup = [
            [sg.Text('Pokemon search')],
            [sg.InputCombo(l, enable_events=True, key='-log-pkmnsearch-')],
            [sg.Button('Search', key='-search-'), sg.Button('Cancel')]
        ] 
        window = sg.Window('Pokemon Search', searchpopup).Finalize()
        
        while True:
            event, values = window.read()

            if (event == sg.WINDOW_CLOSED) or (event == 'Cancel'):
                try:
                    pkmnnum = pokemon.loc[pokemon['NUM'] == p].iloc[0,0]
                except:
                    pkmnnum = 0
                break
            elif event == '-search-':
                try:
                    pkmnnum = lcase.index(values['-log-pkmnsearch-'].casefold())
                except:
                    sg.popup_ok('Pokemon not found.', title='Error')
                    pkmnnum = pokemon.loc[pokemon['NUM'] == p].iloc[0,0]
                break

        window.close()

        return pkmnnum

    graph=sg.Graph(canvas_size=(380,200), graph_bottom_left=(50,10), graph_top_right=(330,240),background_color='black', enable_events=True, key='-log-graph-')

    # r = np.random.randint(0,776)
    # r = 165
    logmoves, mvlist = movelist(pokemon.iloc[pokemonnum,16:])
    logabils, alist = abillist(pokemon.iloc[pokemonnum])
    logevos, elist = evolist(pokemon.iloc[pokemonnum])
    logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[pokemonnum], game, tmcompat_df, tms_df)
    logpivotlocs, logpivotbase1, logpivotbase2, pivottext = pivotlist(game)

    bwidth = 1
    bpad = (1,1,0,0)
    navbar = {}
    if gen == 6:
        bfont = ('Franklin Gothic Medium', 12)
        for i in range(1, 7):
            navbar[i]=[[
                sg.Text(' Pokemon ', enable_events=True, key=f'-lognav-pkmn{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont, justification='c'),
                sg.Text(' Trainers ', enable_events=True, key=f'-lognav-trainer{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont, justification='c'),
                sg.Text(' Pivots ', enable_events=True, key=f'-lognav-pivot{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont, justification='c'),
                sg.Text(' TMs ', enable_events=True, key=f'-lognav-tm{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont, justification='c'),
                # sg.Text(' Info ', enable_events=True, key=f'-lognav-info{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
                sg.Text(' Search ', enable_events=True, key=f'-lognav-search{i}-', relief='groove', border_width=1, pad=bpad, font=bfont, justification='c'),
                # sg.Text(' Random ', enable_events=True, key=f'-lognav-random{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
                sg.Text(' X ', enable_events=True, key=f'-lognav-exit{i}-', relief='groove', border_width=1, pad=bpad, font=bfont, justification='c'),
            ]]
    elif gen == 7: # not complete, will need to fill in later
        bfont = ('Franklin Gothic Medium', 10) # need smaller font because more nav bar things, may choose to go to two rows instead but we'll see if thats needed (hopefully not), could also use abbreviations; might also roll tutor into TM for gen 7
        for i in range(1, 8):
            navbar[i]=[[
                sg.Text(' Pokemon ', enable_events=True, key=f'-lognav-pkmn{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
                sg.Text(' Trainers ', enable_events=True, key=f'-lognav-trainer{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
                sg.Text(' Pivots ', enable_events=True, key=f'-lognav-pivot{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
                sg.Text(' TMs ', enable_events=True, key=f'-lognav-tm{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
                # sg.Text(' Tutors ', enable_events=True, key=f'-lognav-tutor{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
                # sg.Text(' Info ', enable_events=True, key=f'-lognav-info{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
                sg.Text(' Search ', enable_events=True, key=f'-lognav-search{i}-', relief='groove', border_width=1, pad=bpad, font=bfont),
                # sg.Text(' Random ', enable_events=True, key=f'-lognav-random{i}-', relief='groove', border_width=bwidth, pad=bpad, font=bfont),
            ]]


    brcol1 = [[
        sg.Column([
            [sg.Column(logtms1, size=(150,220)),],
            [sg.Column(logabils, size=(170,120))],
        ])
    ]]
    blcol1 = [[
        sg.Column([
            [sg.Column(logmoves, scrollable=True, vertical_scroll_only=True, size=(150,220)),],
            [sg.Column(logevos, size=(170,120))],
        ])
    ]]

    bccol3 = [logpivotbase1]
    brcol3 = [logpivotbase2]

    layout_pkmn = [
        [sg.Column(navbar[1], key='-log-navbar1-', size=(340,35), justification='c')],
        [graph], 
        [
            sg.Column(blcol1, key='-log-blcol-', size=(170,350), pad=(5,0,0,0)),
            sg.Column(brcol1, key='-log-brcol-', size=(170,350), pad=(5,0,0,0))
        ],
    ]

    d,tl,tn = 0,[],[]
    for i in t_dict: # separates the log list of trainers into the dict lists
        tl.append(log_tlist[d:d + len(t_dict[i])])
        tn.append(d) # needed for calls later
        d = d + len(t_dict[i])
    tn.append(d)
    tfont = ('Franklin Gothic Medium', 10)
    tfont2 = ('Franklin Gothic Medium', 12)
    layout_trainers = [
        [sg.Column(navbar[2], key='-log-navbar4-', size=(340,35), justification='c')],
        [
            sg.Text(f' {t_types[0]} ', font=tfont, text_color='white', relief='groove', enable_events=True, key='-log-train-rival-'),
            sg.Text(f' {t_types[1]} ', font=tfont, text_color='#f0f080', relief='groove', enable_events=True, key='-log-train-leader-'),
            sg.Text(f' {t_types[2]} ', font=tfont, text_color='white', relief='groove', enable_events=True, key='-log-train-e4-'),
            sg.Text(f' {t_types[3]} ', font=tfont, text_color='white', relief='groove', enable_events=True, key='-log-train-other-'),
        ],
        [
            sg.Text(f'Trainers:', text_color='#f0f080', font=tfont2, visible = True, size=15), 
            sg.Text(f'PKMN', text_color='#f0f080', font=tfont2, visible = True, size=8), 
            sg.Text(f'LVL', text_color='#f0f080', font=tfont2, visible = True, size=4), 
            sg.Text(f'ITEM', text_color='#f0f080', font=tfont2, visible = True, size=9),
        ],
        [sg.Column([
            [
                sg.Column(tl[0], size=(0,400), key='-log-tcol-0-', visible = True, pad=(0,0,0,0)),
                sg.Column(tl[1], size=(120,400), key='-log-tcol-1-', visible = True, pad=(0,0,0,0)),
                sg.Column(tl[2], size=(0,400), key='-log-tcol-2-', visible = True, pad=(0,0,0,0)),
                sg.Column(tl[3], size=(0,400), key='-log-tcol-3-', visible = True, pad=(0,0,0,0)),
                sg.Column(log_tparty1, size=(90,400)),
                sg.Column(log_tparty2, size=(25,400)),
                sg.Column(log_tparty3, size=(90,400)),
            ],
        ])]
    ]

    layout_pivots = [
        [sg.Column(navbar[3], key='-log-navbar3-', size=(340,35), justification='c')],
        [
            sg.Column(logpivotlocs, key='-log-pivotlocs-', size=(150,350), justification='l'),
            sg.Column(logpivotbase1, size=(100,350)), 
            sg.Column(logpivotbase2, size=(50,350)),
        ], 
    ]

    layout_tms = [
        [sg.Column(navbar[4], key='-log-navbar4-', size=(340,35), justification='c')],
        [sg.Text(f'{pokemon.iloc[pokemonnum,1]} ({sum(pokemon.iloc[pokemonnum,3:9])} BST)', font=('Franklin Gothic Medium', 16), text_color='#f0f080', key='-log-tmpkmn-')],
        [
            sg.Text(f'Gym TMs:', font=('Franklin Gothic Medium', 14), text_color='#f0f080', size=15),
            sg.Text(f'All TMs:', font=('Franklin Gothic Medium', 14), text_color='#f0f080'),
        ],
        [sg.Column([
            [
                sg.Column(logtms4, size=(150,400)),
                sg.Column(logtmsfull, size=(150,400), scrollable=True, vertical_scroll_only=True),
            ],
        ])]
    ]
    # layout_tutors = [
    #     [sg.Column(navbar[5], key='-log-navbar4-', size=(340,35), justification='c')],
    # ]
    # layout_info = [
    #     [sg.Column(navbar[6], key='-log-navbar4-', size=(340,35), justification='c')],
    # ]
    # layout_search = [
    #     [sg.Column(navbar[7], key='-log-navbar4-', size=(340,35), justification='c')],
    # ]

    layout_logview = [[
        sg.Column(layout_pkmn, key='-layout1-'), 
        sg.Column(layout_trainers, key='-layout2-', visible=False), 
        sg.Column(layout_pivots, key='-layout3-', visible=False), 
        sg.Column(layout_tms, key='-layout4-', visible=False), 
    ]]

    window = sg.Window('Ironmon Log Viewer', layout_logview, track_size, finalize=True, element_padding=(1,1,0,0))

    statchart(pokemon.iloc[pokemonnum])
    logmoves, mvlist = movelist(pokemon.iloc[pokemonnum,16:], logmoves, mvlist)
    logabils, alist = abillist(pokemon.iloc[pokemonnum])
    logevos, elist = evolist(pokemon.iloc[pokemonnum])
    logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[pokemonnum], game, tmcompat_df, tms_df)
    # print(tmtext)
    # print(tmtextfull)
    logpivotlocs, logpivotbase1, logpivotbase2, pivottext = pivotlist(game)

    l = 1 #current layout (defaults to pokemon screen)
    t = t_types[1] #current trainer subclass selected (defaults to gym leaders/kahunas)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, f'-lognav-exit{l}-'):
            break
        elif event == f'-lognav-pkmn{l}-':
            window[f'-layout{l}-'].update(visible=False)
            window[f'-lognav-trainer{l}-'].update(text_color='white')
            window[f'-lognav-pivot{l}-'].update(text_color='white')
            window[f'-lognav-tm{l}-'].update(text_color='white')
            l = 1
            window[f'-layout{l}-'].update(visible=True)
            window[f'-lognav-pkmn{l}-'].update(text_color='#f0f080')
        elif event == f'-lognav-trainer{l}-':
            window[f'-layout{l}-'].update(visible=False)
            window[f'-lognav-pkmn{l}-'].update(text_color='white')
            window[f'-lognav-pivot{l}-'].update(text_color='white')
            window[f'-lognav-tm{l}-'].update(text_color='white')
            l = 2
            window[f'-layout{l}-'].update(visible=True)
            window[f'-lognav-trainer{l}-'].update(text_color='#f0f080')
        elif event == f'-lognav-pivot{l}-':
            window[f'-layout{l}-'].update(visible=False)
            window[f'-lognav-trainer{l}-'].update(text_color='white')
            window[f'-lognav-pkmn{l}-'].update(text_color='white')
            window[f'-lognav-tm{l}-'].update(text_color='white')
            l = 3
            window[f'-layout{l}-'].update(visible=True)
            window[f'-lognav-pivot{l}-'].update(text_color='#f0f080')
        elif event == f'-lognav-tm{l}-':
            window[f'-layout{l}-'].update(visible=False)
            window[f'-lognav-trainer{l}-'].update(text_color='white')
            window[f'-lognav-pivot{l}-'].update(text_color='white')
            window[f'-lognav-pkmn{l}-'].update(text_color='white')
            l = 4
            window[f'-layout{l}-'].update(visible=True)
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
        # if event == f'-lognav-tutor{l}-':
        #     window[f'-layout{l}-'].update(visible=False)
        #     l = 5
        #     window[f'-layout{l}-'].update(visible=True)
        # if event == f'-lognav-info{l}-':
        #     window[f'-layout{l}-'].update(visible=False)
        #     l = 6
        #     window[f'-layout{l}-'].update(visible=True)
        elif event == f'-lognav-search{l}-':
            p = searchfcn(pokemon, pkmn_srch)
            graph.Erase()
            statchart(pokemon.iloc[p])
            logmoves, mvlist = movelist(pokemon.iloc[p,16:])
            logabils, alist = abillist(pokemon.iloc[p])
            logevos, elist = evolist(pokemon.iloc[p])
            logtms1, logtms4, logtmsfull, gymtmlist, tmdict, tmdictfull, tmtext, tmtextfull = tmlist(pokemon.iloc[p], game, tmcompat_df, tms_df)
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
            window['-log-tmpkmn-'].update(f'{pokemon.iloc[p,1]} ({sum(pokemon.iloc[p,3:9])} BST)')
        elif event in ('-logpivot-loc0-', '-logpivot-loc1-', '-logpivot-loc2-', '-logpivot-loc3-', '-logpivot-loc4-', '-logpivot-loc5-', '-logpivot-loc6-', '-logpivot-loc7-', '-logpivot-loc8-', '-logpivot-loc9-', '-logpivot-loc10-', '-logpivot-loc11-', '-logpivot-loc12-', '-logpivot-loc13-', '-logpivot-loc14-', '-logpivot-loc15-', '-logpivot-loc16-', '-logpivot-loc17-', '-logpivot-loc18-', '-logpivot-loc19-', '-logpivot-loc20-', '-logpivot-loc21-', '-logpivot-loc22-', '-logpivot-loc23-', '-logpivot-loc24-', '-logpivot-loc25-', '-logpivot-loc26-', '-logpivot-loc27-', '-logpivot-loc28-'):
            n = int(event[-3:].replace('-','').replace('c',''))
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
                set_size(window['-log-tcol-0-'], (120, 400))
                set_size(window['-log-tcol-1-'], (0, 400))
                set_size(window['-log-tcol-2-'], (0, 400))
                set_size(window['-log-tcol-3-'], (0, 400))
            elif event == '-log-train-leader-':
                t = t_types[1]
                set_size(window['-log-tcol-0-'], (0, 400))
                set_size(window['-log-tcol-1-'], (120, 400))
                set_size(window['-log-tcol-2-'], (0, 400))
                set_size(window['-log-tcol-3-'], (0, 400))
            elif event == '-log-train-e4-':
                t = t_types[2]
                set_size(window['-log-tcol-0-'], (0, 400))
                set_size(window['-log-tcol-1-'], (0, 400))
                set_size(window['-log-tcol-2-'], (120, 400))
                set_size(window['-log-tcol-3-'], (0, 400))
            elif event == '-log-train-other-':
                t = t_types[3]
                set_size(window['-log-tcol-0-'], (0, 400))
                set_size(window['-log-tcol-1-'], (0, 400))
                set_size(window['-log-tcol-2-'], (0, 400))
                set_size(window['-log-tcol-3-'], (120, 400))
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

    window.close()

# logloader_solo((425, 580))