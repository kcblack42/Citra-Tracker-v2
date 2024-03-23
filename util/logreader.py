import PySimpleGUI as sg
import json
import pathlib
import pandas as pd
import re
import io
import plotly.express as px
import plotly.graph_objects as go
import numpy as np # this won't actually be needed for launch

track_size = (380, 580)
font_sizes = [14, 12, 10, 15]
sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=150)

'''
Useful demo for swapping entirely different window layouts (it's actually really simple): 
https://pysimplegui.trinket.io/demo-programs#/layouts/swapping-window-layouts

LOG HEADERS:
--Randomized Evolutions--
--Pokemon Base Stats & Types--
--Removing Impossible Evolutions--
--Removing Timed-Based Evolutions--
--Random Starters--
--Move Data--
--Pokemon Movesets--
--TM Moves--
--TM Compatibility--
--Trainers Pokemon--
--Static Pokemon--
--Wild Pokemon--
--In-Game Trades--
--Pickup Items--

might want to consider making a /util/log folder for log layouts and stuff but i'll cross that bridge if/when i get there
'''

log = open('kaizo260.log', encoding="utf8").read()
log.count('\n--')

lsplit = log.split('\n--')
evos = lsplit[1] # done
mons = lsplit[2] # done
moves = lsplit[7] # done
tms = lsplit[8] # done
tmcompat = lsplit[9] # done
trainer = lsplit[10] # done
wildmons = lsplit[12] # done

def parser(data, pattern, s):
    groups = [m.groupdict() for line in data.split(sep=s) if (m := re.match(pattern, line))]
    return groups

# evolutions
evos_regex = r'(?P<preevo>\S+)+\s+(?P<postevo>\S+)?'
evos_df = pd.DataFrame(parser(evos.replace('->', ''), evos_regex, '\n')[1:])

# mons
mons_df = pd.read_csv(io.StringIO(mons.replace('Pokemon Base Stats & Types--','')), sep='|')
mons_df.columns = mons_df.columns.str.strip()
mons_df[mons_df.select_dtypes('object').columns] = mons_df[mons_df.select_dtypes('object').columns].apply(lambda x: x.str.strip())
mons_df[['TYPE1', 'TYPE2']] = mons_df['TYPE'].str.split('/', expand=True)

# tm compatibility
tmcompat_df = pd.read_csv(io.StringIO(tmcompat.replace('TM Compatibility--','')), sep='|', header=None)
tmcompat_df[['NUM', 'NAME']] = tmcompat_df[0].str.strip().str.split(' ', n=1, expand=True)

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
trainer_regex = r"#(?P<number>[0-9]+)\s\((?P<name>[ï\-ç♂♀\&A-Z0-9\sa-z\é\~\[\]]*)\=\>\s[-ïç♂♀a-zA-Z\s\&]*\)\s\-\s(?P<team>.+)"
trainer_df = pd.DataFrame(parser(trainer, trainer_regex, '\n'))
# team_regex = r"(?P<name>\S+)+\s+Lv(?P<level>[0-9]+)"
trainer_team = trainer_df['team'].str.split(',', expand=True)
for (index, colname) in enumerate(trainer_team):
    new_col1 = 'pkmn_' + str(colname + 1)
    new_col2 = 'lvl_' + str(colname + 1)
    trainer_team[[new_col1, new_col2]] = trainer_team[colname].str.split(' Lv', expand=True)
    trainer_team.drop(columns=colname, inplace=True)
trainer_df = pd.concat([trainer_df, trainer_team], axis=1).drop(columns='team')

# wilds
wilds_df = pd.DataFrame(wildmons.replace('Wild Pokemon--\n', '').split('\n\n')).rename(columns={0:'set'})
wilds_df = wilds_df['set'].str.split('\n', expand=True)
wilds_df[['set', 'loc']] = wilds_df[0].str.split('-', expand=True)
wilds_df.drop(columns=0, inplace=True)
for (index, colname) in enumerate(wilds_df.iloc[:, 0:12]):
    new_col1 = 'pkmn_' + str(colname)
    new_col2 = 'lvl_' + str(colname)
    wilds_df[colname] = wilds_df[colname].str[0:24].str.strip()
    wilds_df[[new_col1, new_col2]] = wilds_df[colname].str.split(' Lv', expand=True)
    wilds_df.drop(columns=colname, inplace=True)

# joins for easier event handling later
pokemon = pd.merge(mons_df, evos_df, how = 'left', left_on='NAME', right_on='preevo').drop(columns='preevo').rename(columns={'postevo':'EVOLUTION'})
pokemon = pd.merge(pokemon, moves_df, how='left', left_on='NAME', right_on='mon').drop(columns=['num', 'mon', 'evo'])
pokemon.columns = pokemon.columns.str.replace('col_', 'move_')

# charting stats
pkmn_stats = pokemon[['NAME', 'HP', 'ATK', 'DEF', 'SATK', 'SDEF', 'SPD']].melt(id_vars='NAME')
pkmn = 'Alakazam'
# this is a pretty simple bar chart, for something that's more complicated (and significantly more customized), we'll need the go.Figure and go.Bar combination that's a bit more gross to set up, since we literally have to convert the dataframe into lists, can start with this
# stat_chart = px.bar(pkmn_stats.loc[pkmn_stats['NAME'] == pkmn], x='variable', y='value', range_y=[0, 255], text='value')
# stat_chart


# # var = pkmn_stats.loc[pkmn_stats['NAME'] == pkmn]['variable'].to_list()
# val = pkmn_stats.loc[pkmn_stats['NAME'] == pkmn]['value'].to_list()
# stat_chart2 = go.Figure(data=[go.Bar(
#     x=var,
#     y=val,
#     text=val, 
#     textposition='outside',
# )])
# stat_chart2.update_yaxes(
#     range=[0,255],
#     gridwidth=0,
#     showgrid=False,
#     showticklabels=False,
#     )
# stat_chart2.update_layout(
#     plot_bgcolor='black',
#     paper_bgcolor='black',
#     font_color='white',
#     title=pkmn + ' (' + str(sum(val)) + ' BST)',
#     )
# stat_chart2

def statchart(mon):
    base = 50
    i = 0
    stat = ['HP', 'ATK', 'DEF', 'SATK', 'SDEF', 'SPD']
    for s in mon[3:9]:
        x1 = 70 + (40 * i)
        y1 = base
        x2 = 100 + (40 * i)
        y2 = base + (s * .6)
        if s >= 180:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='green', fill_color='green')
        elif s <= 40:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='red', fill_color='red')
        else:
            graph.draw_rectangle((x1,y1), (x2,y2), line_color='white', fill_color='white')
        graph.DrawText(stat[i], location=((x1 + x2)/2, base-2), color='white', text_location=sg.TEXT_LOCATION_TOP, font=('Franklin Gothic Medium', 12))
        graph.DrawText(s, location=((x1 + x2)/2, y2+2), color='white', text_location=sg.TEXT_LOCATION_BOTTOM, font=('Franklin Gothic Medium', 12))
        i += 1

    graph.DrawText(f'{mon.iloc[1]} ({sum(mon.iloc[3:9])} BST)', location=(70, base+180), color='white', text_location=sg.TEXT_LOCATION_TOP_LEFT, font=('Franklin Gothic Medium', 16))
    graph.DrawLine(point_from=(65,base), point_to=(305,base), color='white')

def movelist(mon, logmoves = [], mvlist = []):
    mon = mon.to_list()
    i = 0
    logmoves = []
    mvlist = []
    while i < len(mon):
        if str(mon[i]) != 'nan':
            mon[i] = str(mon[i]).replace('Level ', '')
            logmoves.append([sg.Text(mon[i], text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-', visible = True)])
            mvlist.append(mon[i])
        else:
            logmoves.append([sg.Text('', text_color='white', font=('Franklin Gothic Medium', 12), key = f'-log-ml{i}-')])
        i += 1
    return logmoves, mvlist

def abillist(mon):
    alist = mon[['ABILITY1', 'ABILITY2', 'ABILITY3']]
    logabils = []
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
    elist = []
    i = 0
    return logevos, elist

graph=sg.Graph(canvas_size=(380,300), graph_bottom_left=(50,10), graph_top_right=(330,240),background_color='black', enable_events=True, key='-log-graph-')

r = np.random.randint(0,776)
logmoves, mvlist = movelist(moves_df.iloc[r,3:])
logabils, alist = abillist(mons_df.iloc[r])
logevos, elist = evolist(mons_df.iloc[r])

layout = [
    [graph], 
    [
        sg.Column(logmoves, scrollable=True, vertical_scroll_only=True, key='-log-moves-', size=(180,280)),
        sg.Column(
            [
                # sg.Column(logleaderTMs, key = '-log-leaderTMs-', size = (180,280))
                sg.Column(logabils, key='-log-abils-', size=(180,160)),
                # sg.Column(logevos, key = '-log-evos-', size = (180,120))
            ]
        )
    ],
    [sg.Button('Randomize')],
]
window = sg.Window('Graph test', layout, track_size, finalize=True)

statchart(mons_df.iloc[r])
logmoves, mvlist = movelist(moves_df.iloc[r,3:], logmoves, mvlist)
logabils, alist = abillist(mons_df.iloc[r])
logevos, elist = evolist(mons_df.iloc[r])

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED:
        break
    if event == 'Randomize':
        i = 0
        x = np.random.randint(0,776)
        graph.Erase()
        statchart(mons_df.iloc[x])
        logmoves, mvlist = movelist(moves_df.iloc[x,3:], logmoves, mvlist)
        logabils, alist = abillist(mons_df.iloc[x])
        logevos, elist = evolist(mons_df.iloc[x])
        while i < len(logmoves):
            if i < len(mvlist):
                window[f'-log-ml{i}-'].update(mvlist[i], visible = True)
            else:
                window[f'-log-ml{i}-'].update(visible = False)
            if i < len(alist) and i == 2:
                window[f'-log-al{i}-'].update(f'{alist.iloc[i]} (HA)', visible = True)
            elif i < len(alist):
                window[f'-log-al{i}-'].update(alist.iloc[i], visible = True)
            i += 1
        # window.refresh()


window.close()