import PySimpleGUI as sg
import json

scale = 1.3
font_sizes = [14, 12, 10, 15]
sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=200, scaling=scale)

def settings_ui():
    try:
        settingsfile=r"settings.json"
    except:
        settingsfile = {'batch_path':'', 'mod_path':'', 'prefix':''}

def autoload_settings():
    try:
        settingsfile=r"settings.json"
        settingsdict=json.load(open(settingsfile,"r+"))
    except:
        settingsdict = {'batch_path':'', 'mod_path':'', 'prefix':''}

    layout = [
            [
                sg.Text("Batch folder:", size=15), 
                sg.Input(settingsdict['batch_path'], key="-batch-path-"), 
                sg.FolderBrowse(key="-browse1-"),
            ],
            [
                sg.Text("Citra mod folder:", size=15), 
                sg.Input(settingsdict['mod_path'], key="-mod-path-"), 
                sg.FolderBrowse(key="-browse2-"),
            ],
            [
                sg.Text("File name prefix:", size=15), 
                sg.Input(settingsdict['prefix'], key="-prefix-", size=25),
            ],
            [sg.Button("Submit")]
        ]

    window = sg.Window('Autoload Settings', layout)
        
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event=="Exit":
            break
        elif event == "Submit":
            settingsdict['batch_path'] = values["-batch-path-"]
            settingsdict['mod_path'] = values["-mod-path-"]
            settingsdict['prefix'] = values["-prefix-"]
            break

    window.close()
    
    with open(settingsfile,'w+') as f:
        json.dump(settingsdict,f)
    
    print(settingsdict['batch_path'])
    print(settingsdict['mod_path'])
    print(settingsdict['prefix'])


# b, s = autoload_settings()
# print(b, ';;;', s)
# open('settings.txt', 'w+').writelines(["batch_path='", b, "'\n", "mod_path='", s, "'"])
