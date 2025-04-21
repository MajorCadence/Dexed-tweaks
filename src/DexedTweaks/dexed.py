
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
    Create a MIDI connection to a device. (this will initialize the global midi_output_object)
    :param name: The name of the MIDI device. If this is not a virtual device, this is the name of the port to connect to.
    :param virtual: Whether to create a virtual MIDI device. Virtual MIDI devices are not supported by every API. Default is True.
    :param number: The number of the MIDI device to connect to. Default is 0.
    :param client_name: The name of the client. Default is None.
    :param API: The MIDI API to use. Default is rtmidi.API_LINUX_ALSA. Please refer to the rtmidi documentation for other options (windows, mac).
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
    Close the MIDI connection. Provided for convinience.
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
    :param channel: The DX7 'channel' to send on, if you have multiple. Default for Dexed is 0, but can be changed.
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
    """
    Represents a single oscillator in a Dexed voice.
    """
    def __init__(self, number: int, active: bool = True, **kwargs):
        """
        Initializes the Oscillator object.
        :param number: The number of the oscillator (1-6).
        :param active: Whether the oscillator is active or not. Default is True.
        :param kwargs: Additional keyword argument(s). Must be 'data': A list of integers representing raw oscillator data. The oscillator will internally populatethe data until it is full or the list is empty.
        """
        if number > 6 or number < 1:
            raise ValueError('Oscillator number (ID) must be between 1 and 6')
            number = 1
        self.number: int = number
        self._oscillator_data: list = [0 for _ in range(21)]
        self.active: bool = active
        """Whether the oscillator is active or not. Default is True."""
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
                        if type(kwargs['data']) != list and type(kwargs['data']) != bytes:
                            raise TypeError(f'Data must be a list of integers or a byte object, not {type(kwargs['data'])}')
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
        """
        The EG_RATE_1 parameter. Valid values are between 0 and 99.
        :return: The EG_RATE_1 value.
        """
        return self._oscillator_data[0]
    @EG_RATE_1.setter
    def EG_RATE_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[0] = value
    @property
    def EG_RATE_2(self):
        """
        The EG_RATE_2 parameter. Valid values are between 0 and 99.
        :return: The EG_RATE_2 value.
        """
        return self._oscillator_data[1]
    @EG_RATE_2.setter
    def EG_RATE_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[1] = value
    @property
    def EG_RATE_3(self):
        """
        The EG_RATE_3 parameter. Valid values are between 0 and 99.
        :return: The EG_RATE_3 value.
        """
        return self._oscillator_data[2]
    @EG_RATE_3.setter
    def EG_RATE_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[2] = value
    @property
    def EG_RATE_4(self):
        """
        The EG_RATE_4 parameter. Valid values are between 0 and 99.
        :return: The EG_RATE_4 value.
        """
        return self._oscillator_data[3]
    @EG_RATE_4.setter
    def EG_RATE_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[3] = value
    @property
    def EG_LEVEL_1(self):
        """
        The EG_LEVEL_1 parameter. Valid values are between 0 and 99.
        :return: The EG_LEVEL_1 value.
        """
        return self._oscillator_data[4]
    @EG_LEVEL_1.setter
    def EG_LEVEL_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[4] = value
    @property
    def EG_LEVEL_2(self):
        """
        The EG_LEVEL_2 parameter. Valid values are between 0 and 99.
        :return: The EG_LEVEL_2 value.
        """
        return self._oscillator_data[5]
    @EG_LEVEL_2.setter
    def EG_LEVEL_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[5] = value
    @property
    def EG_LEVEL_3(self):
        """
        The EG_LEVEL_3 parameter. Valid values are between 0 and 99.
        :return: The EG_LEVEL_3 value.
        """
        return self._oscillator_data[6]
    @EG_LEVEL_3.setter
    def EG_LEVEL_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[6] = value
    @property
    def EG_LEVEL_4(self):
        """
        The EG_LEVEL_4 parameter. Valid values are between 0 and 99.
        :return: The EG_LEVEL_4 value.
        """
        return self._oscillator_data[7]
    @EG_LEVEL_4.setter
    def EG_LEVEL_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[7] = value
    @property
    def Breakpoint(self):
        """
        The oscillator breakpoint parameter. Valid values are between 0 and 99. 39 = C3.
        :return: The Breakpoint value.
        """
        return self._oscillator_data[8]
    @Breakpoint.setter
    def Breakpoint(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[8] = value
    @property
    def Left_Depth(self):
        """
        The left scale depth parameter. Valid values are between 0 and 99.
        :return: The Left_Depth value.
        """
        return self._oscillator_data[9]
    @Left_Depth.setter
    def Left_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[9] = value
    @property
    def Right_Depth(self):
        """
        The right scale depth parameter. Valid values are between 0 and 99.
        :return: The Right_Depth value.
        """
        return self._oscillator_data[10]
    @Right_Depth.setter
    def Right_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[10] = value
    @property
    def Left_Curve(self):
        """
        The left scale curve parameter. Valid values are between 0 and 3. 0 is a negative linear curve, 1 is a negative exponetial curve, 2 is a positive exponential curve, and 3 is a positive linear curve.
        :return: The Left_Curve value.
        """
        return self._oscillator_data[11]
    @Left_Curve.setter
    def Left_Curve(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[11] = value
    @property
    def Right_Curve(self):
        """
        The right scale curve parameter. Valid values are between 0 and 3. 0 is a negative linear curve, 1 is a negative exponetial curve, 2 is a positive exponential curve, and 3 is a positive linear curve.
        :return: The Right_Curve value.
        """
        return self._oscillator_data[12]
    @Right_Curve.setter
    def Right_Curve(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[12] = value
    @property
    def Rate_Scaling(self):
        """
        The rate scaling parameter. Valid values are between 0 and 7.
        :return: The Rate_Scaling value.
        """
        return self._oscillator_data[13]
    @Rate_Scaling.setter
    def Rate_Scaling(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._oscillator_data[13] = value
    @property
    def Amp_Mod_Scaling(self):
        """
        The amplitude modulation scaling parameter. Valid values are between 0 and 3.
        :return: The Amp_Mod_Scaling value.
        """
        return self._oscillator_data[14]
    @Amp_Mod_Scaling.setter
    def Amp_Mod_Scaling(self, value: int):
        if value < 0 or value > 3:
            raise ValueError("This parameter must have a value between 0 and 3")
        self._oscillator_data[14] = value
    @property
    def Key_Velocity(self):
        """
        The key velocity parameter. Valid values are between 0 and 7.
        :return: The Key_Velocity value.
        """
        return self._oscillator_data[15]
    @Key_Velocity.setter
    def Key_Velocity(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._oscillator_data[15] = value
    @property
    def Output_Level(self):
        """
        The output level (oscillator volume) parameter. Valid values are between 0 and 99.
        :return: The Output_Level value.
        """
        return self._oscillator_data[16]
    @Output_Level.setter
    def Output_Level(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[16] = value
    @property
    def Oscillator_Mode(self):
        """
        The oscillator mode parameter. Valid values are 0 (fixed) or 1 (ratio).
        :return: The Oscillator_Mode value.
        """
        return self._oscillator_data[17]
    @Oscillator_Mode.setter
    def Oscillator_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (fixed) or 1 (ratio)")
        self._oscillator_data[17] = value
    @property
    def Frequency_Coarse(self):
        """
        The coarse frequency adjustment parameter. Valid values are between 0 and 31.
        :return: The Frequency_Coarse value.
        """
        return self._oscillator_data[18]
    @Frequency_Coarse.setter
    def Frequency_Coarse(self, value: int):
        if value < 0 or value > 31: 
            raise ValueError("This parameter must have a value between 0 and 31")
        self._oscillator_data[18] = value
    @property
    def Frequency_Fine(self):
        """
        The fine frequency adjustment parameter. Valid values are between 0 and 99.
        :return: The Frequency_Fine value.
        """
        return self._oscillator_data[19]
    @Frequency_Fine.setter
    def Frequency_Fine(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._oscillator_data[19] = value
    @property
    def Detune(self):
        """
        The detune parameter. Valid values are between 0 and 14. A value of 7 is no detune.
        :return: The Detune value.
        """
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
        """
        Returns the MIDI address of the specified parameter. For use with the send_dexed_parameter() function.
        :param parameter: The parameter name or index.
        :return: The MIDI address of the parameter.
        """
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
    """
    Represents a global function in Dexed. These are not saved with the voice data. Function parameters differ from voice parameters in the MIDI messaging as well. You should pass in 'function=true' when using send_dexed_parameter() to send a function parameter.
    Function parameters do not currently work with Dexed, but may work with a real DX7.
    """
    def __init__(self):
        """
        Initializes the Function object. This is not part of a voice of cart. Currently, you can only use send_dexed_parameter() to send function parameters.
        """

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
        #Not needed yet, at least until Dexed functionality working
        raise NotImplementedError
    
    def function_data_as_list(self):
        """
        Returns the function data as a list.
        :return: The function data as a list.
        """
        return self._function_data
    

    # Here are the properties for a Dexed Function, mapped into a list ordered in memory
    @property
    def Mono_Poly_Mode(self):
        """
        Monophonic vs. polyphonic mode. Valid values are 0 (polyphonic) or 1 (monophonic).
        :return: The Mono_Poly_Mode value.
        """
        return self._function_data[0]
    @Mono_Poly_Mode.setter
    def Mono_Poly_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (polyphonic mode) or 1 (monophonic mode)")
        self._function_data[0] = value
    @property
    def Pitch_Bend_Range(self):
        """
        Set the range of the pitch bend wheel. Valid values are between 0 and 12. 12 is two full octaves of range.
        :return: The Pitch_Bend_Range value.
        """
        return self._function_data[1]
    @Pitch_Bend_Range.setter
    def Pitch_Bend_Range(self, value: int):
        if value < 0 or value > 12:
            raise ValueError("This parameter must have a value between 0 and 12")
        self._function_data[1] = value
    @property
    def Pitch_Bend_Step(self):
        """
        Set the step of the pitch bend wheel. Valid values are between 0 and 12. 12 is an octave step.
        :return: The Pitch_Bend_Step value.
        """
        return self._function_data[2]
    @Pitch_Bend_Step.setter
    def Pitch_Bend_Step(self, value: int):
        if value < 0 or value > 12:
            raise ValueError("This parameter must have a value between 0 and 12")
        self._function_data[2] = value
    @property
    def Portamento_Mode(self):
        """
        Set the portamento mode. Valid values are 0 (retain: long or sustained notes will not have portamento applied) or 1 (follow: portamento will be applied to all notes when they are released)
        :return: The Portamento_Mode value.
        """
        return self._function_data[3]
    @Portamento_Mode.setter
    def Portamento_Mode(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 or 1")
        self._function_data[3] = value
    @property
    def Portamento_Gliss(self):
        """
        Set the portamento glissando mode. Valid values are 0 (portamento: smooth pitch sliding) or 1 (glissando: stepped pitch sliding)
        :return: The Portamento_Gliss value.
        """
        return self._function_data[4]
    @Portamento_Gliss.setter
    def Portamento_Gliss(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 or 1")
        self._function_data[4] = value
    @property
    def Portamento_Time(self):
        """
        Set the portamento time. Valid values are between 0 and 99. 99 is the longest portamento time. 0 is no effect at all.
        :return: The Portamento_Time value.
        """
        return self._function_data[5]
    @Portamento_Time.setter
    def Portamento_Time(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[5] = value
    @property
    def Mod_Wheel_Range(self):
        """
        Set the modulation wheel range. Valid values are between 0 and 99. 
        :return: The Mod_Wheel_Range value.
        """
        return self._function_data[6]
    @Mod_Wheel_Range.setter
    def Mod_Wheel_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[6] = value
    @property
    def Mod_Wheel_Assign(self):
        """
        Function(s) to assign the modulation wheel to. Valid values are between 0 and 7. Bit 0 sets control over pitch. Bit 1 sets control over amplitude. Bit 2 sets control over EG_Bias (amount?).
        :return: The Mod_Wheel_Assign value.
        """
        return self._function_data[7]
    @Mod_Wheel_Assign.setter
    def Mod_Wheel_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[7] = value
    @property
    def Foot_Control_Range(self, value: int):
        """
        Set the foot control range. Valid values are between 0 and 99.
        :return: The Foot_Control_Range value.
        """
        return self._function_data[8]
    @Foot_Control_Range.setter
    def Foot_Control_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[8] = value
    @property
    def Foot_Control_Assign(self):
        """
        Function(s) to assign the foot control to. Valid values are between 0 and 7. Bit 0 sets control over pitch. Bit 1 sets control over amplitude. Bit 2 sets control over EG_Bias (amount?).
        :return: The Foot_Control_Assign value.
        """
        return self._function_data[9]
    @Foot_Control_Assign.setter
    def Foot_Control_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[9] = value
    @property
    def Breath_Control_Range(self):
        """
        Set the breath control range. Valid values are between 0 and 99.
        :return: The Breath_Control_Range value.
        """
        return self._function_data[10]
    @Breath_Control_Range.setter
    def Breath_Control_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[10] = value
    @property
    def Breath_Control_Assign(self):
        """
        Function(s) to assign the breath control to. Valid values are between 0 and 7. Bit 0 sets control over pitch. Bit 1 sets control over amplitude. Bit 2 sets control over EG_Bias (amount?).
        :return: The Breath_Control_Assign value.
        """
        return self._function_data[11]
    @Breath_Control_Assign.setter
    def Breath_Control_Assign(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._function_data[11] = value
    @property
    def Aftertouch_Range(self):
        """
        Set the aftertouch (modulation via applying pressure to held keys) range. Valid values are between 0 and 99.
        :return: The Aftertouch_Range value.
        """
        return self._function_data[12]
    @Aftertouch_Range.setter
    def Aftertouch_Range(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._function_data[12] = value
    @property
    def Aftertouch_Assign(self):
        """
        Function(s) to assign the aftertouch to. Valid values are between 0 and 7. Bit 0 sets control over pitch. Bit 1 sets control over amplitude. Bit 2 sets control over EG_Bias (amount?).
        :return: The Aftertouch_Assign value.
        """
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
        """
        Returns the MIDI address of the specified parameter. For use with the send_dexed_parameter() function.
        :param parameter: The parameter name.
        :return: The MIDI address of the parameter.
        """
        if not isinstance(parameter, str):
            raise ValueError('Function parameter must be a string to search')
            return -1
        if parameter in self._parameter_indices:
            return self._parameter_indices[parameter] + 64
        else:        
            raise KeyError('Parameter name not found')
            return -1
    
    

class Voice():
    """
    Represents a voice in Dexed. This is the main object for working with Dexed voices. A voice will consist of 6 oscillators, and a set of voice parameters.
    """
    def __init__(self, number: int, oscillators: list[Oscillator] = [], **kwargs):
        """
        Initializes a Voice object.
        :param number: The number of the voice (0-31) within a cart.
        :param oscillators: An optional list of Oscillator objects to initialize the voice with. Default is an empty list.
        :param kwargs: Additional keyword argument(s). Must be either: '
        'name': A string (10 characters max) for the name of the voice. 
        'data': A list of integers representing raw voice data. The voice will internally populate the data until it is full or the list is empty.
        """
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
                        if type(kwargs['data']) != list and type(kwargs['data']) != bytes:
                            raise TypeError(f'Data must be a list of integers or a byte object, not {type(kwargs['data'])}')
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
        """
        The Pitch_EG_Rate_1 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Rate_1 value.
        """
        return self._voice_data[0]
    @Pitch_EG_Rate_1.setter
    def Pitch_EG_Rate_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[0] = value
    @property
    def Pitch_EG_Rate_2(self):
        """
        The Pitch_EG_Rate_2 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Rate_2 value.
        """
        return self._voice_data[1]
    @Pitch_EG_Rate_2.setter
    def Pitch_EG_Rate_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[1] = value
    @property
    def Pitch_EG_Rate_3(self):
        """
        The Pitch_EG_Rate_3 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Rate_3 value.
        """
        return self._voice_data[2]
    @Pitch_EG_Rate_3.setter
    def Pitch_EG_Rate_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[2] = value
    @property
    def Pitch_EG_Rate_4(self):
        """
        The Pitch_EG_Rate_4 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Rate_4 value.
        """
        return self._voice_data[3]
    @Pitch_EG_Rate_4.setter
    def Pitch_EG_Rate_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[3] = value
    @property
    def Pitch_EG_Level_1(self):
        """
        The Pitch_EG_Level_1 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Level_1 value.
        """
        return self._voice_data[4]
    @Pitch_EG_Level_1.setter
    def Pitch_EG_Level_1(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[4] = value
    @property
    def Pitch_EG_Level_2(self):
        """
        The Pitch_EG_Level_2 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Level_2 value.
        """
        return self._voice_data[5]
    @Pitch_EG_Level_2.setter
    def Pitch_EG_Level_2(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[5] = value
    @property
    def Pitch_EG_Level_3(self):
        """
        The Pitch_EG_Level_3 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Level_3 value.
        """
        return self._voice_data[6]
    @Pitch_EG_Level_3.setter
    def Pitch_EG_Level_3(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[6] = value
    @property
    def Pitch_EG_Level_4(self):
        """
        The Pitch_EG_Level_4 parameter. Valid values are between 0 and 99.
        :return: The Pitch_EG_Level_4 value.
        """
        return self._voice_data[7]
    @Pitch_EG_Level_4.setter
    def Pitch_EG_Level_4(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[7] = value
    @property
    def Algorithm(self):
        """
        The algorithm parameter. Valid values are between 0 and 31. This directly corresponds to the number seen in Dexed.
        :return: The Algorithm value.
        """
        return self._voice_data[8]
    @Algorithm.setter
    def Algorithm(self, value: int):
        if value < 0 or value > 31:
            raise ValueError("This parameter must have a value between 0 and 31")
        self._voice_data[8] = value
    @property
    def Feedback(self):
        """
        The feedback parameter (loops output back to input). Valid values are between 0 and 7.
        :return: The Feedback value.
        """
        return self._voice_data[9]
    @Feedback.setter
    def Feedback(self, value: int):
        if value < 0 or value > 7:  
            raise ValueError("This parameter must have a value between 0 and 7")
        self._voice_data[9] = value
    @property
    def Oscillator_Key_Sync(self):
        """
        The oscillator key sync parameter. Resets and syncs oscillators when a new key is pressed (?). Valid values are 0 (no sync) or 1 (sync).
        :return: The Oscillator_Key_Sync value.
        """
        return self._voice_data[10]
    @Oscillator_Key_Sync.setter
    def Oscillator_Key_Sync(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (off) or 1 (on)")
        self._voice_data[10] = value
    @property
    def LFO_Speed(self):
        """
        The LFO speed parameter. Valid values are between 0 and 99.
        :return: The LFO_Speed value.
        """
        return self._voice_data[11]
    @LFO_Speed.setter
    def LFO_Speed(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[11] = value
    @property
    def LFO_Delay(self):
        """
        The LFO delay parameter. Valid values are between 0 and 99.
        :return: The LFO_Delay value.
        """
        return self._voice_data[12]
    @LFO_Delay.setter
    def LFO_Delay(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[12] = value
    @property
    def LFO_Pitch_Mod_Depth(self):
        """
        The LFO pitch modulation depth parameter. Valid values are between 0 (no modulation) and 99 (maximum modulation).
        :return: The LFO_Pitch_Mod_Depth value.
        """
        return self._voice_data[13]
    @LFO_Pitch_Mod_Depth.setter
    def LFO_Pitch_Mod_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[13] = value
    @property
    def LFO_Amp_Mod_Depth(self):
        """
        The LFO amplitude modulation depth parameter. Valid values are between 0 (no modulation) and 99 (maximum modulation).
        :return: The LFO_Amp_Mod_Depth value.
        """
        return self._voice_data[14]
    @LFO_Amp_Mod_Depth.setter
    def LFO_Amp_Mod_Depth(self, value: int):
        if value < 0 or value > 99:
            raise ValueError("This parameter must have a value between 0 and 99")
        self._voice_data[14] = value
    @property
    def LFO_Key_Sync(self):
        """
        The LFO key sync parameter. Resets LFO when new key is pressed. Valid values are 0 (no sync) or 1 (sync).
        :return: The LFO_Key_Sync value.
        """
        return self._voice_data[15]
    @LFO_Key_Sync.setter
    def LFO_Key_Sync(self, value: int):
        if value < 0 or value > 1:
            raise ValueError("This parameter must either be 0 (off) or 1 (on)")
        self._voice_data[15] = value
    @property
    def LFO_Waveform_Shape(self):
        """
        The LFO waveform shape parameter. Valid values are 0 (triangle), 1 (sawtooth down), 2 (sawtooth up), 3 (square), 4 (sine), or 5 (sample and hold; random).
        :return: The LFO_Waveform_Shape value.
        """
        return self._voice_data[16]
    @LFO_Waveform_Shape.setter
    def LFO_Waveform_Shape(self, value: int):
        if value < 0 or value > 5:
            raise ValueError("This parameter must have a value between 0 and 5")
        self._voice_data[16] = value
    @property
    def Pitch_Mod_Sensitivity(self):
        """
        The pitch modulation sensitivity parameter. How much far the pitch modulation spans (?). Valid values are between 0 and 7.
        :return: The Pitch_Mod_Sensitivity value.
        """
        return self._voice_data[17]
    @Pitch_Mod_Sensitivity.setter
    def Pitch_Mod_Sensitivity(self, value: int):
        if value < 0 or value > 7:
            raise ValueError("This parameter must have a value between 0 and 7")
        self._voice_data[17] = value
    @property
    def Transpose(self):
        """
        The transpose parameter. Valid values are between 0 and 48. This is the number of semitones to transpose the voice. A value of 12 corresponds to the note C2.
        :return: The Transpose value.
        """
        return self._voice_data[18]
    @Transpose.setter
    def Transpose(self, value: int):
        if value < 0 or value > 48:
            raise ValueError("This parameter must have a value between 0 and 48")
        self._voice_data[18] = value
    @property
    def Voice_Name(self):
        """
        The name of the voice. Must be a string between 0 and 10 ASCII characters.
        :return: The Voice_Name value.
        """
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
        """A bitmask of the active oscillators contained within the voice. Read only. Use this value in single parameter changes. To update this value, set the active attribute in each oscillator."""
        return int(''.join(['1' if oscillator.active else '0' for oscillator in self.get_oscillators()]), 2)

    def send_to_dexed(self, channel: int = 0) -> bool:
        """
        Sends the voice data to Dexed.
        :param channel: The DX7 'channel' to send on, if you have multiple. Default for Dexed is 0, but can be changed.
        :return: True if the data was sent successfully, False otherwise.
        """
        # Form the MIDI message
        sub_status = 0x00 # leave this as is
        format_n = 0x00 # format for 1 voice

        # total byte count of 155
        byte_count_MSB = 0x01
        byte_count_LSB = 0x1B

        checksum = 0x7F & sum(chain(self.Oscillator1, self.Oscillator2, self.Oscillator3, self.Oscillator4, self.Oscillator5, self.Oscillator6, self._voice_data))
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
        """
        Returns the MIDI address of the specified parameter. For use with the send_dexed_parameter() function.
        :param parameter: The parameter name.
        :return: The MIDI address of the parameter.
        """
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
    """
    Represents a Dexed cart. This is the main object for working with Dexed carts. A Dexed cart consists of 32 voices.
    """
    def __init__(self, voices: list[Voice] = None, filename: str = str | None):
        self._voices = [Voice(i) for i in range(32)]
        if filename is not None:
            self.read_from_file(filename)
        elif voices is not None:
            if all(isinstance(voice, Voice) for voice in voices):
                self._voices = voices
            else:
                raise TypeError('All elements in the voices list must be instances of Voice')

    def read_from_file(self, filename: str) -> None:
        """
        Reads a Dexed cart file and loads the data.
        :param filename: The name of the file to read from.
        :return: None
        """
        with open(filename, 'rb') as f:
            data = f.read()
            if data[:4] != bytes.fromhex('F0430009'):
                raise ValueError('Invalid Dexed cart file format: missing header')
            if data[4:6] != bytes.fromhex('2000'):
                raise ValueError('Invalid Dexed cart file format: missing header')
            if data[-2] != ((-1*sum(data[6:-2])) & 0x7F):
                print('Invalid Dexed cart file format: checksum mismatch! Loading anyway...')
            data = data[6:-2]
            unpacked_data = self._convert_from_32_voice_dump_format(data)
            for i in range(32):
                voice_data = unpacked_data[i*155 + 6*21:(i+1)*155]
                voice = Voice(i, data=voice_data)
                voice.Oscillator6 = Oscillator(6, data=unpacked_data[i*155:i*155 + 21])
                voice.Oscillator5 = Oscillator(5, data=unpacked_data[i*155 + 21:i*155 + 42])
                voice.Oscillator4 = Oscillator(4, data=unpacked_data[i*155 + 42:i*155 + 63])
                voice.Oscillator3 = Oscillator(3, data=unpacked_data[i*155 + 63:i*155 + 84])
                voice.Oscillator2 = Oscillator(2, data=unpacked_data[i*155 + 84:i*155 + 105])
                voice.Oscillator1 = Oscillator(1, data=unpacked_data[i*155 + 105:i*155 + 126])
                self._voices[i] = voice
    def save_to_file(self, filename: str) -> None:
        """
        Saves the cart data to a Dexed cart file.
        :param filename: The name of the file to save to.
        :return: None
        """
        with open(filename, 'wb') as f:
            total_voice_data = [0 for _ in range(32)]
            for i in range(32):
                total_voice_data[i] = chain(self._voices[i].Oscillator6.oscillator_data_to_list(),
                                        self._voices[i].Oscillator5.oscillator_data_to_list(),
                                        self._voices[i].Oscillator4.oscillator_data_to_list(),
                                        self._voices[i].Oscillator3.oscillator_data_to_list(),
                                        self._voices[i].Oscillator2.oscillator_data_to_list(),
                                        self._voices[i].Oscillator1.oscillator_data_to_list(),
                                        self._voices[i].voice_data_to_list())
            packed_data = self._convert_to_32_voice_dump_format(bytes([byte for voice_data in total_voice_data for byte in voice_data]))
            f.write(bytes.fromhex('F04300092000') + packed_data + ((-1*sum(packed_data)) & 0x7F).to_bytes(1, 'big') + bytes.fromhex('F7'))
    def get_voices(self) -> list[Voice]:
        """
        Returns the list of voices contained within this cart.
        :return: The list of Voice objects.
        """
        return self._voices
    
    def get_voices_name(self) -> list[str]:
        """
        Returns the list of voice names contained within this cart.
        :return: The list of Voice names.
        """
        return [voice.Voice_Name for voice in self._voices]

    def send_to_dexed(self, channel: int = 0) -> bool:
        """
        Sends the cart data to Dexed.
        :param channel: The DX7 'channel' to send on, if you have multiple. Default for Dexed is 0, but can be changed.
        :return: True if the data was sent successfully, False otherwise.
        """
        total_voice_data = [0 for _ in range(32)]
        header = bytes.fromhex('F04300092000')
        for i in range(32):
            total_voice_data[i] = chain(self._voices[i].Oscillator6.oscillator_data_to_list(),
                                    self._voices[i].Oscillator5.oscillator_data_to_list(),
                                    self._voices[i].Oscillator4.oscillator_data_to_list(),
                                    self._voices[i].Oscillator3.oscillator_data_to_list(),
                                    self._voices[i].Oscillator2.oscillator_data_to_list(),
                                    self._voices[i].Oscillator1.oscillator_data_to_list(),
                                    self._voices[i].voice_data_to_list())
        packed_data = self._convert_to_32_voice_dump_format(bytes([byte for voice_data in total_voice_data for byte in voice_data]))
        checksum = ((-1*sum(packed_data)) & 0x7F).to_bytes(1, 'big')
        message = chain(header, packed_data, checksum, bytes.fromhex('F7'))
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
        #Active Oscillators parameter doesn't matter here; it's overriden by Dexed when changing voices
        return True
    
    def __getitem__(self, index):
        if index < 0 or index > 31:
            raise IndexError('Index out of range')
        return self._voices[index]
    
    def __setitem__(self, index, value) -> None:
        if not isinstance(value, Voice):
            raise ValueError('Value must be an instance of Voice')
        if index < 0 or index > 31:
            raise IndexError('Index out of range')
        value.number = index # update to ensure that the voice number matches the attribute its assigned to
        self._voices[index] = value

    def _convert_to_32_voice_dump_format(self, data: bytes) -> bytes:
        """
        Converts unpacked byte data to the 32 voice dump format.
        :param data: The data to convert.
        :return: The converted data.
        """
        new_data = bytearray(4096)
        temp_data = bytearray(26)
        for i in range(32):
            voice_data = data[i*155:(i+1)*155]
            for j in range(6):
                oscillator_data = voice_data[21*j:21*(j+1)]
                temp_data[:11] = oscillator_data[:11]
                temp_data[11] = (oscillator_data[11] & 0b11) + ((oscillator_data[12] & 0b11) << 2)
                temp_data[12] = (oscillator_data[13] & 0b111) + ((oscillator_data[20] & 0b1111) << 3)
                temp_data[13] = (oscillator_data[14] & 0b11) + ((oscillator_data[15] & 0b111) << 2)
                temp_data[14] = oscillator_data[16]
                temp_data[15] = (oscillator_data[17] & 0b1) + ((oscillator_data[18] & 0b11111) << 1)
                temp_data[16] = oscillator_data[19]
                new_data[i*128 + j*17:(i*128 + j*17) + 17] = temp_data[:17]
            voice_param_data = voice_data[126:155]
            temp_data[:8] = voice_param_data[:8]
            temp_data[8] = voice_param_data[8] & 0b11111
            temp_data[9] = (voice_param_data[9] & 0b111) + ((voice_param_data[10] & 0b1) << 3)
            temp_data[10:14] = voice_param_data[11:15]
            temp_data[14] = (voice_param_data[15] & 0b1) + ((voice_param_data[16] & 0b1111) << 1) + ((voice_param_data[17] & 0b11) << 5)
            temp_data[15:] = voice_param_data[18:]
            new_data[i*128 + 6*17:(i*128 + 6*17) + 26] = temp_data
                             
        return bytes(new_data)
    
    def _convert_from_32_voice_dump_format(self, data: bytes) -> bytes:
        """
        Converts from the 32 voice dump format to unpacked byte data.
        :param data: The data to convert.
        :return: The converted data.
        """
        new_data = bytearray(4960)
        temp_data = bytearray(26)
        for i in range(32):
            voice_data = data[i*128:(i+1)*128]
            for j in range(6):
                oscillator_data = voice_data[j*17:(j+1)*17]
                temp_data[:11] = oscillator_data[:11]
                temp_data[11] = oscillator_data[11] & 0b11
                temp_data[12] = (oscillator_data[11] & 0b1100) >> 2
                temp_data[13] = oscillator_data[12] & 0b111
                temp_data[14] = oscillator_data[13] & 0b11
                temp_data[15] = (oscillator_data[13] & 0b11100) >> 2
                temp_data[16] = oscillator_data[14]
                temp_data[17] = oscillator_data[15] & 0b1
                temp_data[18] = (oscillator_data[15] & 0b111110) >> 1
                temp_data[19] = oscillator_data[16]
                temp_data[20] = (oscillator_data[12] & 0b1111000) >> 3
                new_data[i*155 + j*21:(i*155 + j*21) + 21] = temp_data[:21]
            voice_param_data = voice_data[6*17:(6*17) + 26]
            temp_data[:8] = voice_param_data[:8]
            temp_data[8] = voice_param_data[8] & 0x1F
            temp_data[9] = voice_param_data[9] & 0b111
            temp_data[10] = (voice_param_data[9] & 0b1000) >> 3
            temp_data[11:15] = voice_param_data[10:14]
            temp_data[15] = voice_param_data[14] & 0b1
            temp_data[16] = (voice_param_data[14] & 0b11110) >> 1
            temp_data[17] = (voice_param_data[14] & 0b1100000) >> 5
            temp_data[18:] = voice_param_data[15:]
            new_data[i*155 + 6*21:(i*155 + 6*21) + 29] = temp_data[:29]
    
        return bytes(new_data)
    

