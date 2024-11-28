EVO_ITEMS = {
    "Eevee": "Any Stone",
    "Gloom": "Leaf Stone/Sun Stone",
    "Poliwhirl": "Water Stone/Kings Rock",
    "Clamperl": "Deep Sea Tooth/Deep Sea Scale",
    "Slowpoke": "Kings Rock/Level 37",
    "Kirlia": "Lvl 30/Dawn Stone (M)"
}

def pkmnEvo(pkmn, key, window):
    if pkmn.evo:
        evofriend = ''
        evolevel = ''
        evostring = ''
        evoloc = ''
        if hasattr(EVO_ITEMS, pkmn.name):
            evoitem = EVO_ITEMS[pkmn.name]
        # need to check snorunt
        else:
            evoitem = ('' if not pkmn.evoitem else 'w/'+pkmn.evoitem)
            evofriend = ('' if pkmn.evotype != 'Friendship' else 'w/ high friendship')
            evolevel = ('' if not pkmn.evolevel else '@ level '+str(int(pkmn.evolevel)))
            evostring = ('' if not pkmn.evostring else pkmn.evostring)
            evoloc = ('' if not pkmn.evolocation else 'in '+pkmn.evolocation)
        window[key].update('>', visible = True)
        window[key].set_tooltip('Evolves {}{}{}{}{}'.format(evoitem, evofriend, evolevel, evostring, evoloc))
    else:
        window[key].update(visible = False)