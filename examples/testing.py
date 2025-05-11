import sys
import os
from time import sleep
import random
import string
# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import DexedTweaks.dexed as dt
from DexedTweaks.dexed import Cart, Oscillator, Voice, Function

# Some info printing functions:
def print_voice_info(voice):
    print("Voice number:", voice.number)
    print("Voice name:", voice.Voice_Name)
    print("Oscillator 1 EG_RATE_1:", voice.Oscillator1.EG_RATE_1)
    print("Oscillator 1 Output Level:", voice.Oscillator1.Output_Level)
    print("Algorithm:", voice.Algorithm)
    print("Feedback:", voice.Feedback)
    print("Active Oscillators bitmask:", bin(voice.ActiveOscillators))
    print("Voice data:", voice.voice_data_to_list())

def print_cart_info(cart):
    print("Cart contains", len(cart.get_voices()), "voices.")
    print("Voice names:", cart.get_voices_name())

if __name__ == "__main__":
    # Example 1: Connect to MIDI (virtual port)

    # Simple way to do it provided by DexedTweaks
    midi = dt.midi_connection("DexedTweaksTest", virtual=True)
    
    # If using a system MIDI port, uncomment the following line:
    #midi = dt.midi_connection("DexedTweaksTest", virtual=False, number=0)

    # Alternatively, you can set this to any rtmidi output connection object:
    #dt.midi_output_object = <your rtmidi.MidiOut object>
    
    print("MIDI connection established.")

    # Example 2: Create and modify an Oscillator
    osc = Oscillator(1)
    osc.EG_RATE_1 = 99
    osc.Output_Level = 80
    print("Oscillator 1 data:", osc.oscillator_data_to_list())

    # Example 3: Create a Voice, set oscillators, and parameters
    voice = Voice(0)
    voice.Oscillator1 = osc
    voice.Algorithm = 5
    voice.Feedback = 3
    voice.Voice_Name = "TestVoice"
    print_voice_info(voice)

    # Example 4: Send a single parameter change to Dexed
    print("Sending parameter change (Oscillator 1 Output Level = 90)...")
    dt.send_dexed_parameter(voice.Oscillator1.midi_addr_of("Output_Level"), 90)

    # Example 5: Send the whole voice to Dexed
    print("Sending full voice to Dexed...")
    voice.send_to_dexed()

    # Example 6: Create a Cart, add voices, and save/load
    cart = Cart()
    cart[0] = voice
    print_cart_info(cart)
    cart.save_to_file("test_cart.syx")
    print("Cart saved to test_cart.syx")

    # Example 7: Load a cart from file
    loaded_cart = Cart(filename="test_cart.syx")
    print("Loaded cart from file:")
    print_cart_info(loaded_cart)

    # Example 8: Send the whole cart to Dexed
    print("Sending cart to Dexed...")
    loaded_cart.send_to_dexed()

    # Example 9: Use Function class to set global parameters (for real DX7, not Dexed)
    func = Function()
    func.Mono_Poly_Mode = 1  # Set to monophonic
    func.Pitch_Bend_Range = 12
    print("Function data:", func.function_data_as_list())
    print("Sending function parameter (Mono/Poly Mode)...")
    dt.send_dexed_parameter(func.midi_addr_of("Mono_Poly_Mode"), func.Mono_Poly_Mode, function_change=True)

    # Example 10: Select a random voice from the cart, set it active
    random_voice_index = random.randint(0, 31)
    cart.dexed_select_voice(random_voice_index)
    print(f"Selected random voice {random_voice_index} from the cart.")

    # Example 11: Clean up MIDI connection
    print("Closing MIDI connection.")
    dt.close_midi_connection()
