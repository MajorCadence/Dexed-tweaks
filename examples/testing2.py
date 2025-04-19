
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
    mycart = Cart()
    for voice in mycart.get_voices():
        voice.Pitch_EG_Rate_1 = 98
        voice.Algorithm = 7
        voice.Voice_Name = ''.join(random.choices(string.ascii_uppercase, k=10))
        print(voice.Voice_Name)
        print(voice.voice_data_to_list())
        for oscillator in voice.get_oscillators():
            oscillator.EG_RATE_1 = 99
            oscillator.Detune = 14
            oscillator.Right_Curve = 3
            oscillator.Left_Curve = 2
            print(oscillator.oscillator_data_to_list())

    mycart.save_to_file("test_cart.dx7")

