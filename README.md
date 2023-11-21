Tracker for Gen 6/7 Pokémon Ironmon.
    Pokémon X/Y, Omega Ruby/Alpha Sapphire, Sun/Moon, Pokémon Ultra Sun/Ultra Moon

How to Use:

Citra emulator for 3DS is required. Drop the files in the folder into the citra scripting folder(the one with a citra.py inside, usually in appdata/local) and run the citra-updater.py file via Python. Citra must have a ROM open (with a pokemon in your party) for the tracker to check for data.

This is currently a separate window that updates automatically every 10 seconds when ran correctly. The party mode automatically displays all the mons in your party, while the left and right arrows scroll between them. If there are any opponent mons, it also displays them and allows note-taking, with some automation.The game is automatically detected.

Hovering/clicking on ceratin areas displays extra data about the mons, such as the move name displaying data about the move.

After a run is over (after you've advanced to the next seed), the way to clear the tracker data before continuing to the next seed is with the notesclear.py file. However, make sure to shut down your ROM before running that file - if you don't, either weird things happen or it will not clear your data at all.

Keep in mind this is an alpha version, do not expect perfection right now. More features will likely be added over time.

Big thanks to brdy for creating the initial display that this was based on, and his database for the data. Additionally, thanks to UTDZac for helping with some of the features being imported from Citra, and [this](https://github.com/EverOddish/PokeStreamer-Tools) for the citra party data.

Python interface is required link [here](https://www.python.org/downloads/).

If you were looking for different games, there are trackers available for the [NDS games](https://github.com/Brian0255/NDS-Ironmon-Tracker)(DPPt, HGSS, BW, B2W2) requiring Bizhawk and the [GBA games](https://github.com/besteon/Ironmon-Tracker)(FRLG, RSE) using Bizhawk or mGBA emulator.
