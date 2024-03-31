import PySimpleGUI as sg
from PIL import Image

def defaultuisettings(font_sizes, logview):
    topcol1 = [
        [sg.Combo([], visible=False, font=('Franklin Gothic Medium', font_sizes[1]), enable_events=True, key='-slotdrop-', readonly=True, expand_x=True, background_color='black', text_color='white')],
        [sg.Text('Loading...', key='-slot-'),],
        [sg.Image(key='-monimg-')], 
        [sg.Text(justification='c', key='-monname-'), sg.Text(font=('Arial', font_sizes[2], 'bold'), key='-monnum-')],
        [sg.Image(key='-typeimg1-'), sg.Text(key='-typename1-'), sg.Image(key='-typeimg2-', visible=False), sg.Text(key='-typename2-', visible=False), sg.Image(key='-typeimg3-', visible=False), sg.Text(key='-typename3-', visible=False),],
        [sg.Text(key='-level-'), sg.Text(key='-evo-', visible = False), sg.Image(key='-status-', visible = False)],
        [sg.Text(key='-ability-')],
        [sg.Text(key='-item-')],
        # [sg.Text(key='-heals-')],
    ]
    topcol2 = [
        [sg.Text(' ', key='-ph1-', visible=True)],
        [sg.Text('HP:', key='-hplabel-', visible=False)],
        [sg.Text('ATK:', key='-attlabel-', visible=False)],
        [sg.Text('DEF:', key='-deflabel-', visible=False)],
        [sg.Text('SPA:', key='-spattlabel-', visible=False)],
        [sg.Text('SPD:', key='-spdeflabel-', visible=False)],
        [sg.Text('SPE:', key='-speedlabel-', visible=False)],
        [sg.Text('BST:', key='-bstlabel-', visible=False)],
        # [sg.Text(key='-heals-')],
    ]
    topcol2b = [
        [sg.Text(key='-hpheals-')],
        # [sg.Text(key='-statusheals-')],
        [sg.Text('Acc: ', key='-accevalabel-', visible=False), sg.Image(key='-accmod-', visible=False), sg.Text('  Eva: ', key='-accevaph-', visible=False), sg.Image(key='-evamod-', visible=False)],
    ]
    topcol3 = [
        [sg.Text(' ', key='-ph2-', visible=True, justification='r')],
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
        [sg.Image(key='-mv1type-'), sg.Text(key='-mv1text-', size=13)],
        [sg.Image(key='-mv2type-'), sg.Text(key='-mv2text-', size=13)],
        [sg.Image(key='-mv3type-'), sg.Text(key='-mv3text-', size=13)],
        [sg.Image(key='-mv4type-'), sg.Text(key='-mv4text-', size=13)],
    ]
    botcol2 = [
        [sg.Text(key='-movepphdr-', size=5, justification='c')],
        [sg.Text(key='-mv1pp-', size=5, justification='r'), sg.Image(key='-mv1mod-'),],
        [sg.Text(key='-mv2pp-', size=5, justification='r'), sg.Image(key='-mv2mod-'),],
        [sg.Text(key='-mv3pp-', size=5, justification='r'), sg.Image(key='-mv3mod-'),],
        [sg.Text(key='-mv4pp-', size=5, justification='r'), sg.Image(key='-mv4mod-'),],
    ]
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
    botcol7 = [
        [
            sg.Button('Next Seed', key='-clearnotes-', font=('Franklin Gothic Medium', font_sizes[2]), pad=(2,2,2,2), auto_size_button=True, visible=False), 
            sg.Button('Batch Settings', key='-settings-', font=('Franklin Gothic Medium', font_sizes[2]), pad=(2,2,2,2), auto_size_button=True, visible=False),
            sg.Button('View Log', key='-view-log-', font=('Franklin Gothic Medium', font_sizes[2]), pad=(2,2,2,2), auto_size_button=True, visible=False)
        ],
    ]

    topcol1a = [
        [sg.Text(key='-slot-e-'),],
        [sg.Image(key='-monimg-e-', enable_events=True)], 
        [sg.Text(justification='c', key='-monname-e-'), sg.Text(font=('Arial', font_sizes[2], 'bold'), key='-monnum-e-')],
        [sg.Image(key='-typeimg1-e-'), sg.Text(key='-typename1-e-'), sg.Image(key='-typeimg2-e-', visible=False), sg.Text(key='-typename2-e-', visible=False),],
        [sg.Text(key='-level-e-'), sg.Text(key='-evo-e-', visible = False), sg.Image(key='-status-e-', visible = False)],
        [sg.Text(key='-ability-e-')],
        [sg.Text(key='-note-e-', text_color='light blue', size=(25,2))],
    ]
    topcol2a = [
        [sg.Text(' ', key='-ph3-')],
        [sg.Text('HP:', key='-hplabel-e-')],
        [sg.Text('ATK:', key='-attlabel-e-')],
        [sg.Text('DEF:', key='-deflabel-e-')],
        [sg.Text('SPA:', key='-spattlabel-e-')],
        [sg.Text('SPD:', key='-spdeflabel-e-')],
        [sg.Text('SPE:', key='-speedlabel-e-')],
        [sg.Text('BST:', key='-bstlabel-e-')],
        # [sg.Text('Acc:', key='-accevalabel-e-'), sg.Image(key='-accmod-e-')],
        # [sg.Button(' + Ability ', key='-addabil-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True)], 
        # [sg.Button('Add Note', key='-addnote-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True)],
    ]
    topcol3a = [
        [sg.Text(' ', key='-ph4-')],
        [sg.Text('[ ]', key='-hp-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Image(key='-attmod-e-'), sg.Text('[ ]', key='-att-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Image(key='-defmod-e-'), sg.Text('[ ]', key='-def-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Image(key='-spattmod-e-'), sg.Text('[ ]', key='-spatt-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Image(key='-spdefmod-e-'), sg.Text('[ ]', key='-spdef-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Image(key='-speedmod-e-'), sg.Text('[ ]', key='-speed-e-', enable_events=True, font=('Consolas', font_sizes[3]))],
        [sg.Text(key='-bst-e-')],
        # [sg.Text('Eva:', key='-accevaph-e-'), sg.Image(key="-evamod-e-")],
        # [sg.Button(' - Ability ', key='-remabil-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True)],
        # [sg.Text('')], 
    ]
    topcol4a = [
        [sg.Text('Acc: ', key='-accevalabel-e-'), sg.Image(key='-accmod-e-'), sg.Text('  Eva: ', key='-accevaph-e-'), sg.Image(key='-evamod-e-')],
        [sg.Button(' + Ability ', key='-addabil-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True), sg.Button(' - Ability ', key='-remabil-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True)], 
        [sg.Button('Add Note', key='-addnote-e-', font=('Franklin Gothic Medium', font_sizes[2]), auto_size_button=True)],
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
        [sg.Text('Pow', key='-movebphdr-e-', size=3, justification='r')],
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
        [sg.Text(key='-abillist-e-', justification='l', font=('Franklin Gothic Medium', font_sizes[2]), text_color="#f0f080")],
        [sg.Text(key='-prevmoves-e-', justification='l', font=('Franklin Gothic Medium', font_sizes[2]), size=(50, 3))],
        # [sg.Text(key='-mv4ctc-e-', size=1, justification='c')],
    ]

    trackerleft = [[
            sg.Column(topcol1, key='-tc1-', size=(200, 350)), 
            sg.Column([[
                sg.Column(topcol2, key='-tc2-', size=(80, 230)), 
                sg.Column(topcol3, element_justification='right', key='-tc3-', size=(100, 230))
                ],
                [
                    sg.Column(topcol2b, key='-tc2b-', size=(180, 120))
                ],
            ])
        ], 
        [
            sg.Column(botcol1, key='-bc1-'), 
            sg.Column(botcol2, key='-bc2-'), 
            sg.Column(botcol4, key='-bc4-'), 
            sg.Column(botcol5, key='-bc5-'),
            sg.Column(botcol6, key='-bc6-'),
        ], 
        [
            sg.Column(botcol7, key='-bc7-'),
        ]]
    
    logviewerleft = logview

    layout_main = [[
        sg.Column(trackerleft, size=(380, 580), key='-lc-'),
        sg.Column(logviewerleft, size=(380, 580), key='-logviewer-', visible=False),
        # sg.VerticalSeparator(key='-vs-'),
        sg.Column([[
            sg.Column(topcol1a, size=(200, 350), key='-tc1a-e-', visible = False), 
            sg.Column([[
                sg.Column(topcol2a, element_justification='right', key='-tc2a-e-', size=(50, 230)), 
                sg.Column(topcol3a, element_justification='right', key='-tc3a-e-', size=(60, 230))
                ],
                [
                    sg.Column(topcol4a, key='-tc4a-e-', size=(140, 120))
                ],
            ], key='-tc2-e-', visible=False),
            # sg.Column(topcol2a, size=(80, 230), key='-tc2a-e-', visible = False), 
            # sg.Column(topcol3a, size=(60, 230), element_justification='right', key='-tc3a-e-', visible = False),
            # sg.Column(topcol4a, size=(140, 120), element_justification='right', key='-tc4a-e-', visible = False),
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
        ]], size=(380, 580), key='-rc-')
    ]]
    return layout_main
