import PySimpleGUI as sg

scale = 1.3
font_sizes = [14, 12, 10, 15]
sg.set_options(font=('Franklin Gothic Medium', font_sizes[0]), text_color='white', background_color='black', element_background_color='black', text_element_background_color='black', tooltip_font=('Franklin Gothic Medium', font_sizes[1]), tooltip_time=200, scaling=scale)

def settings_ui(settings):
    x = 1

def autoload_settings(settings):
    path = {}
    try:
        with open(settings) as f:
            for line in f:
                name, value = line.split('=')
                path[name] = str(value).strip()
    except:
        path['batch_path'] = ''
        path['mod_path'] = ''
        path['prefix'] = ''

    layout = [
            [
                sg.Text("Batch folder:", size=15), 
                sg.Input(path['batch_path'], key="-batch-path-"), 
                sg.FolderBrowse(key="-browse1-"),
            ],
            [
                sg.Text("Citra mod folder:", size=15), 
                sg.Input(path['mod_path'], key="-mod-path-"), 
                sg.FolderBrowse(key="-browse2-"),
            ],
            [
                sg.Text("File name prefix:", size=15), 
                sg.Input(path['prefix'], key="-prefix-", size=25),
            ],
            [sg.Button("Submit")]
        ]

    window = sg.Window('Autoload Settings', layout)
        
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event=="Exit":
            batch_path = path["-batch-path-"]
            mod_path = path["-mod-path-"]
            prefix = path["-prefix-"]
            break
        elif event == "Submit":
            batch_path = values["-batch-path-"]
            mod_path = values["-mod-path-"]
            prefix = values["-prefix-"]
            break

    window.close()

    open(settings, 'w+').writelines(
        [
            "batch_path=", batch_path, "\n", 
            "mod_path=", mod_path, "\n", 
            "prefix=", prefix,  
        ])
    print(batch_path)
    print(mod_path)
    print(prefix)


# b, s = autoload_settings()
# print(b, ';;;', s)
# open('settings.txt', 'w+').writelines(["batch_path='", b, "'\n", "mod_path='", s, "'"])
