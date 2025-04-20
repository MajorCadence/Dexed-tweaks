
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
        for i in range(len(voice.voice_data_to_list())):
            voice[i] = random.randint(0, 127)
        voice.Voice_Name = ''.join(random.choices(string.ascii_uppercase, k=10))
        voice.Transpose = voice.number
        print(voice.Voice_Name)
        print(voice.voice_data_to_list())
        for oscillator in voice.get_oscillators():
            for i in range(len(oscillator.oscillator_data_to_list())):
                oscillator[i] = random.randint(0, 127)
            oscillator.Breakpoint = oscillator.number
            print(oscillator.oscillator_data_to_list())

    mycart.save_to_file("test_cart.dx7")

