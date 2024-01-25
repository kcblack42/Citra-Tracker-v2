import requests
import PySimpleGUI as sg
import webbrowser

def gitcheck(v):
    gitapi = 'https://api.github.com/repos/kcblack42/Citra-Tracker-v2/releases/latest'
    gitlink = 'https://github.com/kcblack42/Citra-Tracker-v2/releases/latest'
    response = requests.get(gitapi)
    gitname = response.json()["name"]
    gittag = response.json()["tag_name"]
    print(v)
    print(gitname)

    vzn = v.replace('v', '').split('.')
    gitvzn = gittag.replace('v', '').split('.')

    if vzn == gitvzn:
        print('Version up to date.')
    elif (vzn[0] > gitvzn[0]):
        print('Version up to date.')
    elif (vzn[1] > gitvzn[1]):
        print('Version up to date.')
    elif (vzn[2] > gitvzn[2]):
        print('Version up to date.')
    else:
        abilpopup = [
            [sg.Text('An update to the tracker is available.')],
            [sg.Button('Visit GitHub', key='-visit-'), sg.Button('Skip')]
        ] 
        window = sg.Window('Update?', abilpopup).Finalize()
        
        while True:
            event, values = window.read()

            if (event == sg.WINDOW_CLOSED) or (event == 'Skip'):
                break
            elif event == '-visit-':
                webbrowser.open(gitlink, new=2)
                break
            else:
                print('OVER')

        window.close()

# gitcheck('v0.5.2')