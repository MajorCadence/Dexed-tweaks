
# dexed-tweaks: A python library for interfacing with Dexed
# Created by MajorCadence 
# (Partially based on code from Waveform.AI project)
# GPL-3.0 License

import rtmidi
from typing import Optional, Callable, Any
from itertools import chain

midi_output_object: Optional[rtmidi.MidiOut] = None
"""This is the global rtmidi object that dexed-tweaks will use for MIDI I/O. 
    Replace this with your own rtmidi object if you want more control. 
    This is automatically set by the midi_connection() function."""

def midi_connection(name: str, virtual: bool = True, number: int = 0, client_name: Optional[str] = None, API: int = rtmidi.API_LINUX_ALSA) -> rtmidi.MidiOut:
    """
    Create a MIDI connection to a device.
    :param name: The name of the MIDI device to connect to.
    :param virtual: Whether to create a virtual MIDI device. Default is True.
    :param number: The number of the MIDI device to connect to. Default is 0.
    :param client_name: The name of the client. Default is None.
    :param API: The MIDI API to use. Default is rtmidi.API_LINUX_ALSA.
    :return: A MidiOut object representing the MIDI connection.
    """
    
    global midi_output_object

    try:
        midi_output_object = rtmidi.MidiOut(API)
    except SystemError as syserr:
        print(f"Error creating MIDI out, possibly unavailable backend API specified: {syserr}")
        midi_output_object = rtmidi.MidiOut(rtmidi.API_UNSPECIFIED)
    if virtual:
        midi_output_object.open_virtual_port(name)
    else:
        midi_output_object.open_port(port=number, name=name)
    if client_name is not None:
        midi_output_object.set_client_name(client_name)
    return midi_output_object

def close_midi_connection() -> None:
    """
    Close the MIDI connection.
    :return: None
    """
    global midi_output_object
    if midi_output_object is not None:
        midi_output_object.close_port()
        midi_output_object = None
    else:
        print("MIDI output object is already closed or not initialized.")


def send_dexed_parameter(parameter: int, value: int | str, function_change: bool = False, channel: int = 0) -> bool:
    """
    Send a parameter value to Dexed. For advanced users.
    :param parameter: The parameter number (MIDI address) to send.
    :param value: The value to send. May be a string in the case of a voice name.
    :param function_change: Whether to send a voice change parameter or a function change parameter. Default is False (voice change).
    :param channel: The MIDI channel to send on. Default is 0.
    :return: True if the message was sent successfully, False otherwise.
    """
    # Check if values are within the valid range
    if type(value) == str:
        if len(value) > 10:
            print('Warning: Value must be a string of 10 ASCII characters or less. Only the first 10 characters will be used.')
            value = value[:10]
        bytes = list(value.encode('ascii'))
    elif type(value) == int:
        bytes = [value]
    else:
        raise TypeError(f"Value must be an integer or a string, not {type(value)}")
    if parameter < 0 or parameter > 155:
        raise ValueError("Parameter must be between 0 and 155")
    if channel < 0 or channel > 15:
        raise ValueError("Channel must be between 0 and 15")
    if function_change:
        if parameter < 64 or parameter > 77:
            print('Warning: Dexed only recognizes function changes between 64 and 77.')
    for value_byte in bytes:
        if value_byte < 0 or value_byte > 127:
            print("Value must be between 0 and 127. Only using the lower 7 bits.")
            value_byte= value_byte & 0x7F
        # Form the MIDI message
        sub_status = 0x01 # leave this as is
        voice_change = 0x8 if function_change else 0
        message = [0xF0, 0x43, sub_status * 16 + channel, voice_change + ((parameter >> 7) & 0x03), parameter & 0x7F, value_byte, 0xF7]
        print([(byte, bin(byte), hex(byte)) for byte in message])
        parameter += 1
        # Send the message
        try:
            if midi_output_object is None:
                raise RuntimeError("MIDI output not initialized. Call midi_connection() first.")
            midi_output_object.send_message(message)
        except RuntimeError as err:
            print(f"Error: {err}")
            return False
        except rtmidi.RtMidiError as err:
            print(f"Error sending MIDI message: {err}")
            return False
        
    return True

class Oscillator():
    def __init__(self, number: int, active: bool = True, **kwargs):
        if number > 6 or number < 1:
            raise ValueError('Oscillator number (ID) must be between 1 and 6')
            number = 1
        self.number: int = number
        self._oscillator_data: list = [0 for _ in range(21)]
        self.active: bool = active
        self._parameter_indices: dict[str, int] = {
            "EG_RATE_1": 0,
            "EG_RATE_2": 1,
            "EG_RATE_3": 2,
            "EG_RATE_4": 3,
            "EG_LEVEL_1": 4,
            "EG_LEVEL_2": 5,
            "EG_LEVEL_3": 6,
            "EG_LEVEL_4": 7,
            "Breakpoint": 8,
            "Left_Depth": 9,
            "Right_Depth": 10,
            "Left_Curve": 11,
            "Right_Curve": 12,
            "Rate_Scaling": 13,
            "Amp_Mod_Scaling": 14,
            "Key_Velocity": 15,
            "Output_Level": 16,
            "Oscillator_Mode": 17,
            "Frequency_Coarse": 18,
            "Frequency_Fine": 19,
            "Detune": 20,
        }
        match len(kwargs):
            case 0:
                pass
            case 1:
                match list(kwargs.keys())[0]:
                    case 'data':
                        if type(kwargs['data']) != list:
                            raise TypeError(f'Data must be a list of integers, not {type(kwargs['data'])}')
                        if not all(type(elem) == int for elem in kwargs['data']):
                            raise TypeError(f'Data must be a list of integers, not {type(kwargs['data'])}')
                        for i in range(min(len(self._oscillator_data), len(kwargs['data']))):
                            self._oscillator_data[i] = kwargs['data'][i]
                    case _:
                        raise ValueError('Unexpected keyword argument in constructor')
            case _:
                raise ValueError('Unexpected number of arguments in constructor')

    # Here are the properties for a Dexed Oscillator, mapped into a list ordered in memory
    @property
    def EG_RATE_1(self):
        return self._oscillator_data[0]
    @EG_RATE_1.setter
    def EG_RATE_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[0] = value
    @property
    def EG_RATE_2(self):
        return self._oscillator_data[1]
    @EG_RATE_2.setter
    def EG_RATE_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[1] = value
    @property
    def EG_RATE_3(self):
        return self._oscillator_data[2]
    @EG_RATE_3.setter
    def EG_RATE_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[2] = value
    @property
    def EG_RATE_4(self):
        return self._oscillator_data[3]
    @EG_RATE_4.setter
    def EG_RATE_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[3] = value
    @property
    def EG_LEVEL_1(self):
        return self._oscillator_data[4]
    @EG_LEVEL_1.setter
    def EG_LEVEL_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[4] = value
    @property
    def EG_LEVEL_2(self):
        return self._oscillator_data[5]
    @EG_LEVEL_2.setter
    def EG_LEVEL_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[5] = value
    @property
    def EG_LEVEL_3(self):
        return self._oscillator_data[6]
    @EG_LEVEL_3.setter
    def EG_LEVEL_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[6] = value
    @property
    def EG_LEVEL_4(self):
        return self._oscillator_data[7]
    @EG_LEVEL_4.setter
    def EG_LEVEL_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[7] = value
    @property
    def Breakpoint(self):
        return self._oscillator_data[8]
    @Breakpoint.setter
    def Breakpoint(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[8] = value
    @property
    def Left_Depth(self):
        return self._oscillator_data[9]
    @Left_Depth.setter
    def Left_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[9] = value
    @property
    def Right_Depth(self):
        return self._oscillator_data[10]
    @Right_Depth.setter
    def Right_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[10] = value
    @property
    def Left_Curve(self):
        return self._oscillator_data[11]
    @Left_Curve.setter
    def Left_Curve(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[11] = value
    @property
    def Right_Curve(self):
        return self._oscillator_data[12]
    @Right_Curve.setter
    def Right_Curve(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[12] = value
    @property
    def Rate_Scaling(self):
        return self._oscillator_data[13]
    @Rate_Scaling.setter
    def Rate_Scaling(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._oscillator_data[13] = value
    @property
    def Amp_Mod_Scaling(self):
        return self._oscillator_data[14]
    @Amp_Mod_Scaling.setter
    def Amp_Mod_Scaling(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[14] = value
    @property
    def Key_Velocity(self):
        return self._oscillator_data[15]
    @Key_Velocity.setter
    def Key_Velocity(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._oscillator_data[15] = value
    @property
    def Output_Level(self):
        return self._oscillator_data[16]
    @Output_Level.setter
    def Output_Level(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[16] = value
    @property
    def Oscillator_Mode(self):
        return self._oscillator_data[17]
    @Oscillator_Mode.setter
    def Oscillator_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (fixed) or 1 (ratio)")
        self._oscillator_data[17] = value
    @property
    def Frequency_Coarse(self):
        return self._oscillator_data[18]
    @Frequency_Coarse.setter
    def Frequency_Coarse(self, value: int):
        if value < 0 or value > 31: 
            raise ValueError("This parameter must have a value between 0 and 31")
        self._oscillator_data[18] = value
    @property
    def Frequency_Fine(self):
        return self._oscillator_data[19]
    @Frequency_Fine.setter
    def Frequency_Fine(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[19] = value
    @property
    def Detune(self):
        return self._oscillator_data[20]
    @Detune.setter
    def Detune(self, value: int):
        if value < 0 or value > 14:
            raise ValueError("This parameter must have a value between 0 and 14")
        self._oscillator_data[20] = value

    def oscillator_data_to_list(self) -> list[int]:
        """
        Returns the oscillator data as a list.
        :return: The oscillator data as a list.
        """
        return self._oscillator_data
    
    def __getitem__(self, index):
        if index < 0 or index > 20:
            raise IndexError('Index out of range')
            return -1
        return self._oscillator_data[index]
    
    def __setitem__(self, index, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError('Value must be an integer')
            return
        self._oscillator_data[index] = 0xFF & abs(value) # make sure it's the size of a byte

    def midi_addr_of(self, parameter: str | int) -> int:
        if isinstance(parameter, int):
            return list(self._parameter_indices.values())[parameter] + 21*(6-self.number)
        elif isinstance(parameter, str):
            if parameter in self._parameter_indices:
                return self._parameter_indices[parameter] + 21*(6-self.number)
            else:        
                raise KeyError('Parameter name not found')
                return -1
        else:
            raise ValueError('Oscillator parameter must be an integer index or a string to search')
            return -1
        
 

class Function():
    def __init__(self):
        self._function_data: list = [0 for _ in range(14)]
        self._parameter_indices = {
        "Mono_Poly_Mode": 0,
        "Pitch_Bend_Range": 1,
        "Pitch_Bend_Step": 2,
        "Portamento_Mode": 3,
        "Portamento_Gliss": 4,
        "Portamento_Time": 5,
        "Mod_Wheel_Range": 6,
        "Mod_Wheel_Assign": 7,
        "Foot_Control_Range": 8,
        "Foot_Control_Assign": 9,
        "Breath_Control_Range": 10,
        "Breath_Control_Assign": 11,
        "Aftertouch_Range": 12,
        "Aftertouch_Assign": 13,
    }

    def send_to_dexed(self):
        raise NotImplementedError
    
    def function_data_as_list(self):
        raise NotImplementedError
    

    # Here are the properties for a Dexed Function, mapped into a list ordered in memory
    @property
    def Mono_Poly_Mode(self):
        return self._function_data[0]
    @Mono_Poly_Mode.setter
    def Mono_Poly_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (polyphonic mode) or 1 (monophonic mode)")
        self._function_data[0] = value
    @property
    def Pitch_Bend_Range(self):
        return self._function_data[1]
    @Pitch_Bend_Range.setter
    def Pitch_Bend_Range(self, value: int):
        if value < 0 or value > 12:
            raise ValueError("This parameter must have a value between 0 and 12")
        self._function_data[1] = value
    @property
    def Pitch_Bend_Step(self):
        return self._function_data[2]
    @Pitch_Bend_Step.setter
    def Pitch_Bend_Step(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[2] = value
    @property
    def Portamento_Mode(self):
        return self._function_data[3]
    @Portamento_Mode.setter
    def Portamento_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (retain) or 1 (follow)")
        self._function_data[3] = value
    @property
    def Portamento_Gliss(self):
        return self._function_data[4]
    @Portamento_Gliss.setter
    def Portamento_Gliss(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (portamento) or 1 (glissando)")
        self._function_data[4] = value
    @property
    def Portamento_Time(self):
        return self._function_data[5]
    @Portamento_Time.setter
    def Portamento_Time(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[5] = value
    @property
    def Mod_Wheel_Range(self):
        return self._function_data[6]
    @Mod_Wheel_Range.setter
    def Mod_Wheel_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[6] = value
    @property
    def Mod_Wheel_Assign(self):
        return self._function_data[7]
    @Mod_Wheel_Assign.setter
    def Mod_Wheel_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[7] = value
    @property
    def Foot_Control_Range(self, value: int):
        return self._function_data[8]
    @Foot_Control_Range.setter
    def Foot_Control_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[8] = value
    @property
    def Foot_Control_Assign(self):
        return self._function_data[9]
    @Foot_Control_Assign.setter
    def Foot_Control_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[9] = value
    @property
    def Breath_Control_Range(self):
        return self._function_data[10]
    @Breath_Control_Range.setter
    def Breath_Control_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[10] = value
    @property
    def Breath_Control_Assign(self):
        return self._function_data[11]
    @Breath_Control_Assign.setter
    def Breath_Control_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[11] = value
    @property
    def Aftertouch_Range(self):
        return self._function_data[12]
    @Aftertouch_Range.setter
    def Aftertouch_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[12] = value
    @property
    def Aftertouch_Assign(self):
        return self._function_data[13]
    @Aftertouch_Assign.setter
    def Aftertouch_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[13] = value
    
    def function_data_to_list(self) -> list[int]:
        """
        Returns the function data as a list.
        :return: The function data as a list.
        """
        return self._function_data
    
    def __getitem__(self, index):
        if index < 0 or index > 13:
            raise IndexError('Index out of range')
            return -1
        return self._function_data[index]
    
    def __setitem__(self, index, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError('Value must be an integer')
            return
        self._function_data[index] = 0xFF & abs(value)

    def midi_addr_of(self, parameter: str) -> int:
        if not isinstance(parameter, str):
            raise ValueError('Function parameter must be a string to search')
            return -1
        if parameter in self._parameter_indices:
            return self._parameter_indices[parameter] + 64
        else:        
            raise KeyError('Parameter name not found')
            return -1
    
    

class Voice():
    def __init__(self, number: int, oscillators: list[Oscillator] = [], **kwargs):
        if number > 31 or number < 0:
            raise ValueError('Voice number (ID) must be between 0 and 31')
            number = 0
        self.number: int = number
        self._voice_data: list = [0 for _ in range(29)]
        self._voice_parameter_indices: dict[str, int] = {
            "Pitch_EG_Rate_1": 0,
            "Pitch_EG_Rate_2": 1,
            "Pitch_EG_Rate_3": 2,
            "Pitch_EG_Rate_4": 3,
            "Pitch_EG_Level_1": 4,
            "Pitch_EG_Level_2": 5,
            "Pitch_EG_Level_3": 6,
            "Pitch_EG_Level_4": 7,
            "Algorithm": 8,
            "Feedback": 9,
            "Oscillator_Key_Sync": 10,
            "LFO_Speed": 11,
            "LFO_Delay": 12,
            "LFO_Pitch_Mod_Depth": 13,
            "LFO_Amp_Mod_Depth": 14,
            "LFO_Key_Sync": 15,
            "LFO_Waveform_Shape": 16,
            "Pitch_Mod_Sensitivity": 17,
            "Transpose": 18,
            "Voice_Name": 19,  # Starting index for the name
            "ActiveOscillators": 29,
        }
        match len(kwargs):
            case 0:
                pass
            case 1:
                match list(kwargs.keys())[0]:
                    case 'name':
                        if type(kwargs['name']) != str:
                            raise TypeError(f'Name must be of type string, not {type(kwargs['name'])}')
                        self.Voice_Name = kwargs['name']
                    case 'data':
                        if type(kwargs['data']) != list:
                            raise TypeError(f'Data must be a list of integers, not {type(kwargs['data'])}')
                        if not all(type(elem) == int for elem in kwargs['data']):
                            raise TypeError(f'Data must be a list of integers, not {type(kwargs['data'])}')
                        for i in range(min(len(self._voice_data), len(kwargs['data']))):
                            self._voice_data[i] = kwargs['data'][i]
                    case _:
                        raise ValueError('Unexpected keyword argument in constructor')
            case _:
                raise ValueError('Unexpected number of arguments in constructor')
        self.Oscillator1 = Oscillator(1)
        self.Oscillator2 = Oscillator(2)
        self.Oscillator3 = Oscillator(3)
        self.Oscillator4 = Oscillator(4)
        self.Oscillator5 = Oscillator(5)
        self.Oscillator6 = Oscillator(6)
        self.set_oscillators(oscillators)
                    
    def get_oscillators(self) -> list[Oscillator]:
        """
        Returns a list of the oscillators in the voice.
        :return: A list of Oscillator objects."""
        return [self.Oscillator1, self.Oscillator2, self.Oscillator3, self.Oscillator4, self.Oscillator5, self.Oscillator6]

    def set_oscillators(self, oscillators: list[Oscillator]) -> None:
        """
        Sets the oscillators in the voice. If the list is shorter than 6, the remaining oscillators will be unchanged.
        :param oscillators: A list of Oscillator objects to set.
        :return: None"""
        for i in range(min(len(oscillators), 6)):
            self.__setattr__(f'Oscillator{i+1}', oscillators[i])

    # Here are the properties for a Dexed Voice, mapped into a list ordered in memory
    @property
    def Pitch_EG_Rate_1(self):
        return self._voice_data[0]
    @Pitch_EG_Rate_1.setter
    def Pitch_EG_Rate_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[0] = value
    @property
    def Pitch_EG_Rate_2(self):
        return self._voice_data[1]
    @Pitch_EG_Rate_2.setter
    def Pitch_EG_Rate_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[1] = value
    @property
    def Pitch_EG_Rate_3(self):
        return self._voice_data[2]
    @Pitch_EG_Rate_3.setter
    def Pitch_EG_Rate_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[2] = value
    @property
    def Pitch_EG_Rate_4(self):
        return self._voice_data[3]
    @Pitch_EG_Rate_4.setter
    def Pitch_EG_Rate_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[3] = value
    @property
    def Pitch_EG_Level_1(self):
        return self._voice_data[4]
    @Pitch_EG_Level_1.setter
    def Pitch_EG_Level_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[4] = value
    @property
    def Pitch_EG_Level_2(self):
        return self._voice_data[5]
    @Pitch_EG_Level_2.setter
    def Pitch_EG_Level_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[5] = value
    @property
    def Pitch_EG_Level_3(self):
        return self._voice_data[6]
    @Pitch_EG_Level_3.setter
    def Pitch_EG_Level_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[6] = value
    @property
    def Pitch_EG_Level_4(self):
        return self._voice_data[7]
    @Pitch_EG_Level_4.setter
    def Pitch_EG_Level_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[7] = value
    @property
    def Algorithm(self):
        return self._voice_data[8]
    @Algorithm.setter
    def Algorithm(self, value: int):
        if value < 0 or value > 31:
            raise ValueError("This parameter must have a value between 0 and 31")
        self._voice_data[8] = value
    @property
    def Feedback(self):
        return self._voice_data[9]
    @Feedback.setter
    def Feedback(self, value: int):
        if value < 0 or value > 7:  
            raise ValueError("This parameter must have a value between 0 and 7")
        self._voice_data[9] = value
    @property
    def Oscillator_Key_Sync(self):
        return self._voice_data[10]
    @Oscillator_Key_Sync.setter
    def Oscillator_Key_Sync(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (off) or 1 (on)")
        self._voice_data[10] = value
    @property
    def LFO_Speed(self):
        return self._voice_data[11]
    @LFO_Speed.setter
    def LFO_Speed(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[11] = value
    @property
    def LFO_Delay(self):
        return self._voice_data[12]
    @LFO_Delay.setter
    def LFO_Delay(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[12] = value
    @property
    def LFO_Pitch_Mod_Depth(self):
        return self._voice_data[13]
    @LFO_Pitch_Mod_Depth.setter
    def LFO_Pitch_Mod_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[13] = value
    @property
    def LFO_Amp_Mod_Depth(self):
        return self._voice_data[14]
    @LFO_Amp_Mod_Depth.setter
    def LFO_Amp_Mod_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[14] = value
    @property
    def LFO_Key_Sync(self):
        return self._voice_data[15]
    @LFO_Key_Sync.setter
    def LFO_Key_Sync(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (off) or 1 (on)")
        self._voice_data[15] = value
    @property
    def LFO_Waveform_Shape(self):
        return self._voice_data[16]
    @LFO_Waveform_Shape.setter
    def LFO_Waveform_Shape(self, value: int):
        if value < 0 or value > 5:
            raise ValueError("This parameter must have a value between 0 and 5")
        self._voice_data[16] = value
    @property
    def Pitch_Mod_Sensitivity(self):
        return self._voice_data[17]
    @Pitch_Mod_Sensitivity.setter
    def Pitch_Mod_Sensitivity(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._voice_data[17] = value
    @property
    def Transpose(self):
        return self._voice_data[18]
    @Transpose.setter
    def Transpose(self, value: int):
        if value < 0 or value > 48:
            raise ValueError("This parameter must have a value between 0 and 48")
        self._voice_data[18] = value
    @property
    def Voice_Name(self):
        return bytes(self._voice_data[19:29]).decode('ascii')
    @Voice_Name.setter
    def Voice_Name(self, name: str):
        if len(name) > 10:
            print('Warning: Voice name cannot be longer than 10 ASCII characters and will be truncated')
            name = name[:10]
        buffer = list(' ' * 10)  # Create a buffer of 10 spaces
        for i, char in enumerate(name):
            buffer[i] = char
        self._voice_data[19:29] = list(''.join(buffer).encode('ascii'))
    @property
    def ActiveOscillators(self):
        """Read only. Use this value in single parameter changes. To update this value, set the active attribute in each oscillator."""
        return int(''.join(['1' if oscillator.active else '0' for oscillator in self.get_oscillators()]), 2)

    def send_to_dexed(self, channel: int = 0) -> bool:
        """
        Sends the voice data to Dexed.
        :param channel: The MIDI channel to send the data on (0-15).
        :return: True if the data was sent successfully, False otherwise.
        """
        # Form the MIDI message
        sub_status = 0x00 # leave this as is
        format_n = 0x00 # format for 1 voice

        # total byte count of 155
        byte_count_MSB = 0x01
        byte_count_LSB = 0x1B

        checksum = 0x7F & (sum(chain([sub_status * 16 + channel, format_n, byte_count_MSB, byte_count_LSB], self.Oscillator1, self.Oscillator2, self.Oscillator3, self.Oscillator4, self.Oscillator5, self.Oscillator6, self._voice_data)) * (-1) + 1)
        message = chain([0xF0, 0x43, sub_status * 16 + channel, format_n, 
                         byte_count_MSB, byte_count_LSB], self.Oscillator1, 
                         self.Oscillator2, self.Oscillator3, self.Oscillator4, 
                         self.Oscillator5, self.Oscillator6, self._voice_data, 
                         [checksum, 0xF7])
        #print([(byte, bin(byte), hex(byte)) for byte in message])
        #Send the message
        try:
            if midi_output_object is None:
                raise RuntimeError("MIDI output not initialized. Call midi_connection() first.")
                return False
            midi_output_object.send_message(message)
        except RuntimeError as err:
            print(f"Error: {err}")
            return False
        except rtmidi.RtMidiError as err:
            print(f"Error sending MIDI message: {err}")
            return False
        # Here we also need to send a single parameter for the active oscillators
        send_dexed_parameter(self.midi_addr_of('ActiveOscillators'), self.ActiveOscillators, channel)
        return True
    
    def voice_data_to_list(self) -> list[int]:
        """
        Returns the voice data as a list.
        :return: The voice data as a list.
        """
        return self._voice_data

    def __setattr__(self, name, value):
        if name.startswith('Oscillator'):
            if not isinstance(value, Oscillator):
                raise ValueError(f'Value must be an instance of Oscillator, not {type(value)}')
            value.number = int(name[-1]) # update to ensure that the oscillator number matches the attribute its assigned to
            self.__dict__[name] = value
        else:
            super().__setattr__(name, value)

    def __getitem__(self, index):
        if index < 0 or index > 28:
            raise IndexError('Index out of range')
        return self._voice_data[index]
    
    def __setitem__(self, index, value) -> None:
        if not isinstance(value, int):
            raise ValueError('Value must be an integer')
        if index < 0 or index > 28:
            raise IndexError('Index out of range')
        self._voice_data[index] = 0xFF & abs(value)
    
    def midi_addr_of(self, parameter: str) -> int:
        if isinstance(parameter, int):
            return list(self._voice_parameter_indices.values())[parameter] + 21*6
        elif isinstance(parameter, str):
            if parameter in self._voice_parameter_indices:
                return self._voice_parameter_indices[parameter] + 21*6
            else:        
                raise KeyError('Parameter name not found')
                return -1
        else:
            raise ValueError('Oscillator parameter must be an integer index or a string to search')
            return -1
        
        

class Cart():
    def __init__(self, voices: list[Voice] = None, filename: str = None):
        if filename is not None:
            self.read_from_file(filename)
        elif voices is not None:
            if all(isinstance(voice, Voice) for voice in voices):
                self._voices = voices
            else:
                raise TypeError('All elements in the voices list must be instances of Voice')
        else:
            self._voices = [Voice(i) for i in range(32)]

    def read_from_file(self, filename: str) -> None:
        """
        Reads a Dexed cart file and populates the voices list.
        :param filename: The name of the file to read from.
        :return: None
        """
        with open(filename, 'rb') as f:
            data = f.read()
            unpacked_data = self._convert_from_32_voice_dump_format(data)
            for i in range(32):
                voice_data = unpacked_data[i*128 + 6*21:(i+1)*128]
                voice = Voice(i, data=voice_data)
                voice.Oscillator1 = Oscillator(1, data=unpacked_data[0:21])
                voice.Oscillator2 = Oscillator(2, data=unpacked_data[21:42])
                voice.Oscillator3 = Oscillator(3, data=unpacked_data[42:63])
                voice.Oscillator4 = Oscillator(4, data=unpacked_data[63:84])
                voice.Oscillator5 = Oscillator(5, data=unpacked_data[84:105])
                voice.Oscillator6 = Oscillator(6, data=unpacked_data[105:126])
                self._voices[i] = voice
    def save_to_file(self, filename: str) -> None:
        """
        Saves the voices to a Dexed cart file.
        :param filename: The name of the file to save to.
        :return: None
        """
        with open(filename, 'wb') as f:
            total_voice_data = [0 for _ in range(32)]
            for i in range(32):
                total_voice_data[i] = chain(self._voices[i].Oscillator1.oscillator_data_to_list(),
                                        self._voices[i].Oscillator2.oscillator_data_to_list(),
                                        self._voices[i].Oscillator3.oscillator_data_to_list(),
                                        self._voices[i].Oscillator4.oscillator_data_to_list(),
                                        self._voices[i].Oscillator5.oscillator_data_to_list(),
                                        self._voices[i].Oscillator6.oscillator_data_to_list(),
                                        self._voices[i].voice_data_to_list())
            packed_data = self._convert_to_32_voice_dump_format(bytes([byte for voice_data in total_voice_data for byte in voice_data]))
            f.write(bytes.fromhex('F04300092000') + packed_data + (-1*sum(packed_data) & 0x7F).to_bytes(1, 'big') + bytes.fromhex('F7'))
    def get_voices(self) -> list[Voice]:
        """
        Returns the list of voices.
        :return: The list of Voice objects.
        """
        return self._voices
    
    def send_to_dexed(self):
        raise NotImplementedError
    
    def __getitem__(self, index):
        if index < 0 or index > 31:
            raise IndexError('Index out of range')
        return self._voices[index]
    
    def __setitem__(self, index, value) -> None:
        if not isinstance(value, Voice):
            raise ValueError('Value must be an instance of Voice')
        if index < 0 or index > 31:
            raise IndexError('Index out of range')
        self._voices[index] = value

    def _convert_to_32_voice_dump_format(self, data: bytes) -> bytes:
        new_data = bytearray(4096)
        temp_data = bytearray(26)
        for i in range(32):
            voice_data = data[i*155:(i+1)*155]
            for j in range(6):
                oscillator_data = voice_data[21*j:21*(j+1)]
                temp_data[:11] = oscillator_data[:11]
                temp_data[11] = oscillator_data[11] + (oscillator_data[12] << 2)
                temp_data[12] = oscillator_data[13] + (oscillator_data[20] << 3)
                temp_data[13] = oscillator_data[14] + (oscillator_data[15] << 2)
                temp_data[14] = oscillator_data[16]
                temp_data[15] = oscillator_data[17] + (oscillator_data[18] << 1)
                temp_data[16] = oscillator_data[19]
                new_data[i*128 + j*17:(i*128 + j*17) + 17] = temp_data[:17]
            voice_param_data = voice_data[126:155]
            temp_data[:9] = voice_param_data[:9]
            temp_data[9] = voice_param_data[9] + (voice_param_data[10] << 3)
            temp_data[10:14] = voice_param_data[11:15]
            temp_data[14] = voice_param_data[15] + (voice_param_data[16] << 1) + (voice_param_data[17] << 5)
            temp_data[15:] = voice_param_data[18:]
            new_data[i*128 + 6*17:(i*128 + 6*17) + 26] = temp_data
                             
        return new_data
    
    def _convert_from_32_voice_dump_format(self, data: bytes) -> bytes:
        """
        Converts the data from the 32 voice dump format.
        :param data: The data to convert.
        :return: The converted data.
        """
        # This is a placeholder implementation
        return data
    

'''
    def __init__(self, preset_path: str = None):
        if preset_path is not None:
            self.__preset_path = preset_path
            with open(preset_path, 'rb') as preset_file:
                self.__rawsysex = preset_file.read()
        self.__pre_init()
        
    def __del__(self):
        del self

    def parse_from_file(self, preset_path: str, index: int):
        if self.__rawsysex == None:
            with open(preset_path, 'rb') as preset_file:
                self.__rawsysex = preset_file.read()
                self.l.debug(f"Loaded preset file {preset_path}")
        assert index >= 0 & index < 32
        removed_header_footer = self.__rawsysex.removeprefix(bytes.fromhex('F04300092000'))[:-2]
        message_at_index = removed_header_footer[128*index : 128*(index + 1)]
        self.l.debug(message_at_index.hex(' '))
        self.l.debug(message_at_index.__len__())
        for i in range(6):
            osc_bytes = message_at_index[17*i:17*(i+1)]
            self.l.debug2(osc_bytes.hex(' '))
            self.__subset = self.__values[21*i:21*(i+1)]
            self.__subset[0:4] = list(osc_bytes[0:4])
            self.__subset[4:8] = list(osc_bytes[4:8])
            self.l.debug(self.__subset)

            self.__values[21*i:21*(i+1)] = self.__subset
        self.l.debug(pformat(self.__values))
        for key, val in self.params.items():
            self.params[key][1] = self.__values[val[0]]
            print(val[0], key, self.__values[val[0]])
        self.l.debug2(f"Updated parameters from parsing: {pformat(self.params)}")

    def parse(self, index: int):
        assert self.__preset_path is not None
        self.parse_from_file(self.__preset_path, index)

    

    def __pre_init(self):
        with open('./data/dexed-mapping.json', 'r') as jfile:
            jdata = jfile.read()
        self.params: dict[str, list[int, int]] = json.loads(jdata)
        self.__values: list[int] = [0 for _ in self.params]
        self.l.debug('Loaded JSON Dexed mapping descriptions!')
        self.l.debug2(pformat(self.params))'
        '''
