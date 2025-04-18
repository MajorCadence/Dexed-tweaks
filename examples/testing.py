
import sys
import os
from time import sleep
import random
import string
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import DexedTweaks.dexed as dt
from DexedTweaks.dexed import Cart, Oscillator, Voice


if __name__ == "__main__":
    # Test the midi_connection function
    midi_out = dt.midi_connection("dexed-tweaks", virtual=False, number=0)
    print(f"MIDI Output: {midi_out}")
    
    # Test sending a parameter to Dexed
    input()
    myvoice = Voice(0, name='prince')
    addr2 = myvoice.midi_addr_of("Voice_Name")
    addr3 = myvoice.midi_addr_of("ActiveOscillators")
    for oscillator in myvoice.get_oscillators():
        oscillator.active = True
    while True:
        for oscillator in myvoice.get_oscillators():
            addr = oscillator.midi_addr_of("Oscillator_Mode")
            dt.send_dexed_parameter(addr, oscillator.Oscillator_Mode)
            dt.send_dexed_parameter(addr2, myvoice.Voice_Name)
            dt.send_dexed_parameter(addr3, myvoice.ActiveOscillators)
            sleep(0.5)
            oscillator.Oscillator_Mode ^= 1
            oscillator.active ^= 1
            randstr = ''.join(random.choices(string.ascii_letters, k=10))
            myvoice.Voice_Name = randstr
            print(myvoice.Voice_Name)
            print(myvoice.ActiveOscillators)
    