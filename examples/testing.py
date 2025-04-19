
import sys
import os
from time import sleep
import random
import string
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import DexedTweaks.dexed as dt
from DexedTweaks.dexed import Cart, Oscillator, Voice, Function


if __name__ == "__main__":
    # Test the midi_connection function
    midi_out = dt.midi_connection("dexed-tweaks", virtual=False, number=0)
    print(f"MIDI Output: {midi_out}")
    
    # Test sending a parameter to Dexed
    
    myvoice = Voice(0, name='prince')
    global_functions = Function()
    for oscillator in myvoice.get_oscillators():
        oscillator.active = True
        oscillator.Oscillator_Mode = 1
    value = 0
    input()
    while True:
        for oscillator in myvoice.get_oscillators():
            for i in range(len(oscillator.oscillator_data_to_list())):
                addr = oscillator.midi_addr_of(i)
                oscillator[i] = value
                dt.send_dexed_parameter(addr, oscillator[i], False)
                sleep(0.01)
        for i in range(len(myvoice._voice_parameter_indices) - 1):
            addr = myvoice.midi_addr_of(i)
            myvoice[i] = value
            dt.send_dexed_parameter(addr, myvoice[i], False)
            sleep(0.01)
        value ^= 1
            