### INSTALLATION INSTRUCTIONS ###

1. Drop all of these files into the same location as citra.py. This is usually in appdata/local.
2. Get a pokemon from the bag/lab/etc.
3. Run the tracker (go to the folder you just dropped your stuff in and try to open the citra-updater.py file)! That's it!

### FOR SEED AUTO-ADVANCEMENT ###

1. Get a dedicated folder where you save your seeds that you batch generate. If you've run a lot of gen 6+ already, you probably have one of these, but if you don't, I tend to like to put it in the same folder as the randomizer. This is your "batch folder".
2. Find your citra mods folder. It should be somewhere like %appdata%/roaming/citra/load/mods or something like that. This is your "mods folder".
3. Note down the "prefix" of your batch seed generation. In the randomizer, it should be directly underneath the place you declare where to batch generate to.

<div><img src="https://github.com/kcblack42/Citra-Tracker-v2/blob/main/images/screens/setup1.png" height="282" width="617" /></div>
<div><img src="https://github.com/kcblack42/Citra-Tracker-v2/blob/main/images/screens/setup2.png" height="47" width="314" /></div>

4. Generate a bunch of seeds using the randomizer in your batch folder from above, but be sure to use the LayeredFS option. If you've used .cxis in the past, this will be MUCH faster (and WAY smaller in size), as it effectively just mods your game rather than creating entirely new ROMs.

<div><img src="https://github.com/kcblack42/Citra-Tracker-v2/blob/main/images/screens/setup3.png" height="122" width="495" /></div>

5. In the tracker, if you click the "Batch Settings" button, you'll be prompted to fill in the three things I mentioned above. Do so and then click "Submit".
6. When your run inevitably dies, use the "Next Seed" button, and it should both clear the saved tracker data, delete your old log + run files, and move your new run file to the folder you designated as the "mods folder" above. The order in which I do this in is click "Next seed", then close the rom, then confirm that you're moving to the next seed, then restart the rom. If you have a save file, you'll obviously need to reset that as well (up + X + B on the title screen). Enjoy your hands-off 3DS ironmon seed advancement experience!
