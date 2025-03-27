
# dexed-tweaks: A python library for interfacing with Dexed
# Created by MajorCadence 
# (Partially based on code from Waveform.AI project)

import rtmidi

def midi_connection():
    pass

def send_dexed_parameter():
    pass

def send_dexed_function_parameter():
    pass

class Voice():
    def __init__(self):
        raise NotImplementedError

    def __del__(self):
        raise NotImplementedError

    def send_to_dexed(self):
        raise NotImplementedError
    
    def voice_data_as_list(self):
        raise NotImplementedError

class Cart():
    def __init__(self):
        raise NotImplementedError

    def __del__(self):
        raise NotImplementedError

    def read_from_file(self, filename: str) -> None:
        raise NotImplementedError

    def save_to_file(self, filename: str) -> None:
        raise NotImplementedError
    
    def get_voice(self, index: int) -> Voice:
        raise NotImplementedError
    
    def get_voices(self) -> list[Voice]:
        raise NotImplementedError
    
    def save_voice(self, index: int, voice: Voice):
        raise NotImplementedError
    
    def send_to_dexed(self):
        raise NotImplementedError
    


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
