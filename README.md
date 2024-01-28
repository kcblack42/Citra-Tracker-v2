Tracker for Gen 6/7 Pokémon Ironmon.
    Pokémon X/Y, Omega Ruby/Alpha Sapphire, Sun/Moon, Pokémon Ultra Sun/Ultra Moon

How to Use/Installation:

Citra emulator for 3DS is required. Drop the files in the folder into the citra scripting folder (the one with a citra.py inside, usually in appdata/local), follow the instructions included (install-instructions.txt) and then run the citra-updater.py file via Python. Citra must have a ROM open (with a pokemon in your party) for the tracker to check for data. Wait until you get a mon to open it for the first time. It will remain open between runs, throwing an error (this is expected) until you get a new mon.

This is currently a separate window that updates automatically every 10 seconds (or whenever you interact with it) when ran correctly. You choose which mon of your own party to view using the drop-down menu, and can see your enemy's primary mon and take notes on abilities, stats, etc. Due to initial limitations, only the enemy's first mon is shown, which causes some issues in doubles (only one mon appears), and it does not function at all in multis and "event" wild encounters. It is a known bug that I'm looking into (so far unsuccessfully). Hovering/clicking on certain areas displays extra data about the mons - i.e. hovering over the move name displays a description of the move.

After a run is over (after your mon has died to bullshit or something), the way to clear the tracker data and then continue to the next seed is with the "Next Seed" button. This does require a bit of setup - see the [install instructions](https://github.com/kcblack42/Citra-Tracker-v2/blob/main/install-instructions.md) for more information. If you're getting errors and have set everything up, please reach out to me (@Kaiya KC) with questions. Additionally, practical rules and strings for gen 6 runs in particular can be found over at [Jellisky's website](https://wterwey.github.io/gen6rulesets.html).

Keep in mind this is an early version (especially for gen 7), do not expect perfection right now. More features will likely be added over time. If you have problems or suggestions, reach out to me (@Kaiya KC) in the ironmon discord, either in the #xy-oras, #sm-usum, or #tracker-dev-chat channels. I'm around way too much.

Big thanks to brdy for creating the initial display that this was based on, and his database for the data. Additionally, thanks to UTDZac for helping with some of the features being imported from Citra, and [this](https://github.com/EverOddish/PokeStreamer-Tools) for the citra party data. And thanks to Accrueblue for putting everything together the first time, none of this would be remotely possible without all of this pre-work.

Python interface is required link [here](https://www.python.org/downloads/). BE SURE TO ADD YOUR PYTHON TO PATH WHEN PROMPTED IN THE INSTALL.

If you were looking for different games, there are trackers available for the [NDS games](https://github.com/Brian0255/NDS-Ironmon-Tracker)(DPPt, HGSS, BW, B2W2) requiring Bizhawk and the [GBA games](https://github.com/besteon/Ironmon-Tracker)(FRLG, RSE) using Bizhawk or mGBA emulator.
