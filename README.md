# Dexed-tweaks

Now you can interface with Dexed from your own Python code! Dexed-tweaks is a simple Python package to load/save/edit entire user-created Dexed carts, single voices, individual parameter tweaking, as well as altering other Dexed functionality. *Should* support a real Yamaha DX7 as well, according to documentation.

Uses rtmidi backend to format SYSEX messages directly to [Dexed](https://github.com/asb2m10/dexed/tree/master). Formatting implemented from the [Dexed documentation](https://github.com/asb2m10/dexed/blob/master/Documentation/sysex-format.txt).

Having looked for a while in vain for something similar to this, I decided to just create it myself and share it. Based on my code from the [WaveformAI project](https://waveformai.wm.edu).

Licensed under GPL3

Eventially this will be installable from pip. Currently under development. ~60% complete.

Most functions have decent documentation. For more info, please look in the examples directory.


## Important Note Regarding Function Parameters and Limitations
Currently, while Dexed voice parameters work great, Dexed does not seem to support changing global function parameters (e.g. pitch bend, aftertouch, portamento, poly/mono switching, etc...). I have still implemented this functionality into my code, and it *should* work with a real DX7, but it is untested. I would appriciate any feedback here.

Dexed unfortunately cannot be prompted to dump the currently loaded Cart over MIDI automatically (at least not to my knowledge), without right-clicking in the cart selector and choosing 'send sysex cartridge to DX7'. Likewise, with the real DX7 you also have to press a button, as opposed to some other synths, (e.g. like the TX7) which support automatic dumping requests.
