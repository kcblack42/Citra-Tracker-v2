Tracker for Gen 6/7 Pokémon Ironmon.
    Pokémon X/Y, Omega Ruby/Alpha Sapphire, Sun/Moon, Pokémon Ultra Sun/Ultra Moon

How to Use:

Citra emulator for 3DS is required. Drop the files in the folder into the citra scripting folder(the one with a citra.py inside, usually in appdata/local) and run the citra-updater.py file via Python. Citra must have a ROM open (with a pokemon in your party) for the tracker to check for data.

This is currently a separate window that updates automatically every 10 seconds when ran correctly. The party mode automatically displays all the mons in your party, while the left and right arrows scroll between them. If there are any opponent mons, it also displays them and allows note-taking, with some automation.The game is automatically detected.

Hovering/clicking on ceratin areas displays extra data about the mons, such as the move name displaying data about the move.

After a run is over (after you've advanced to the next seed), the way to clear the tracker data before continuing to the next seed is with the notesclear.py file. However, make sure to shut down your ROM before running that file - if you don't, either weird things happen or it will not clear your data at all.

Keep in mind this is an alpha version, do not expect perfection right now. More features will likely be added over time.

Big thanks to brdy for creating the initial display that this was based on, and his database for the data. Additionally, thanks to UTDZac for helping with some of the features being imported from Citra, and [this](https://github.com/EverOddish/PokeStreamer-Tools) for the citra party data. And thanks to Accrueblue for putting everything together the first time, none of this would be remotely possible without all of this pre-work.

Python interface is required link [here](https://www.python.org/downloads/). BE SURE TO ADD YOUR PYTHON TO PATH WHEN PROMPTED IN THE INSTALL. In addition, after you've installed python, you'll need to open a command prompt (start menu -> cmd) and type "py -m pip install Pillow". It'll install the "PIL" package that will allow resizing of images. I'm currently working on a better way of distributing this section of the tracker, but this is what we've got to work with.

If you were looking for different games, there are trackers available for the [NDS games](https://github.com/Brian0255/NDS-Ironmon-Tracker)(DPPt, HGSS, BW, B2W2) requiring Bizhawk and the [GBA games](https://github.com/besteon/Ironmon-Tracker)(FRLG, RSE) using Bizhawk or mGBA emulator.
