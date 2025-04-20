
import sys
import os
from time import sleep
import random
import string

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import DexedTweaks
from DexedTweaks.dexed import Cart, Oscillator, Voice, Function


if __name__ == "__main__":
    # Test the midi_connection function
    midi_out = DexedTweaks.dexed.midi_connection("dexed-tweaks", virtual=False, number=0)
    print(f"MIDI Output: {midi_out}")
    
    # Test sending a parameter to Dexed
    mycart = Cart(filename="/home/majorcadence/.local/share/DigitalSuburban/Dexed/Cartridges/Dexed_01.syx")
    mycart.get_voices()[0].Oscillator4.active = False
    mycart.get_voices()[5].send_to_dexed()
    mycart.save_to_file('Dexed_01.syx')

