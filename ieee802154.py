"""
    Copyright (c) 2018 Amar Abane (a_abane@hotmail.fr). All rights reserved.
    This file is part of PyNDN802.15.4.
    This code has been adapted from the Xbee Python library (2010) by Paul Malmsten, Greg Rapp, Brian, Amit Synderman, Marco Sangalli.    
"""

import struct, threading, time

class ThreadQuitException(Exception):
    pass

class CommandFrameException(KeyError):
    pass


def byteToInt(byte):
	if hasattr(byte, 'bit_length'):		
		return byte
	return ord(byte) if hasattr(byte, 'encode') else byte[0]
	
def intToByte(i):
	return chr(i) if hasattr(bytes(), 'encode') else bytes([i])

def stringToBytes(s):
	return s.encode('ascii')


class APIFrame:    
    START_BYTE = b'\x7E'
    ESCAPE_BYTE = b'\x7D'
    XON_BYTE = b'\x11'
    XOFF_BYTE = b'\x13'
    ESCAPE_BYTES = (START_BYTE, ESCAPE_BYTE, XON_BYTE, XOFF_BYTE)
    
    def __init__(self, data=b'', escaped=False):
        self.data = data
        self.raw_data = b''
        self.escaped = escaped
        self._unescape_next_byte = False
        
    def checksum(self):      
        total = 0          
        for byte in self.data:
            total += byteToInt(byte)
        total = total & 0xFF    
        return intToByte(0xFF - total)
    def verify(self, chksum):       
        total = 0
        for byte in self.data:
            total += byteToInt(byte)
        total += byteToInt(chksum)
        total &= 0xFF
        return total == 0xFF

    def len_bytes(self):        
        count = len(self.data)
        return struct.pack("> h", count)
        
    def output(self):                
        data = self.len_bytes() + self.data + self.checksum()        
        if self.escaped and len(self.raw_data) < 1:
            self.raw_data = APIFrame.escape(data)
        if self.escaped:
            data = self.raw_data
        return APIFrame.START_BYTE + data

    @staticmethod
    def escape(data):
        escaped_data = b""
        for byte in data:
            if intToByte(byteToInt(byte)) in APIFrame.ESCAPE_BYTES:
                escaped_data += APIFrame.ESCAPE_BYTE
                escaped_data += intToByte(0x20 ^ byteToInt(byte))
            else:
                escaped_data += intToByte(byteToInt(byte))                
        return escaped_data

    def fill(self, byte):        
        if self._unescape_next_byte:
            byte = intToByte(byteToInt(byte) ^ 0x20)
            self._unescape_next_byte = False
        elif self.escaped and byte == APIFrame.ESCAPE_BYTE:
            self._unescape_next_byte = True
            return
        self.raw_data += intToByte(byteToInt(byte))

    def remaining_bytes(self):
        remaining = 3
        if len(self.raw_data) >= 3:            
            raw_len = self.raw_data[1:3]
            data_len = struct.unpack("> h", raw_len)[0]
            remaining += data_len            
            remaining += 1
        return remaining - len(self.raw_data)
        
    def parse(self):        
        if len(self.raw_data) < 3:
            ValueError("parse() may only be called on a frame containing at least 3 bytes of raw data (see fill())")
        raw_len = self.raw_data[1:3]
        data_len = struct.unpack("> h", raw_len)[0]
        data = self.raw_data[3:3 + data_len]
        chksum = self.raw_data[-1]
        self.data = data
        if not self.verify(chksum):
            raise ValueError("Invalid checksum")


class IEEE802154:
    api_commands = {"tx_long_addr":
                        [{'name':'id',              'len':1,        'default':b'\x00'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr',       'len':8,        'default':None},
                         {'name':'options',         'len':1,        'default':b'\x00'},
                         {'name':'data',            'len':None,     'default':None}],
                    "tx":
                        [{'name':'id',              'len':1,        'default':b'\x01'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr',       'len':2,        'default':None},
                         {'name':'options',         'len':1,        'default':b'\x00'},
                         {'name':'data',            'len':None,     'default':None}]
                    }
    
    api_responses = {b"\x80":
                        {'name':'rx_long_addr',
                         'structure':
                            [{'name':'source_addr', 'len':8},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'rf_data',     'len':None}]},
                     b"\x81":
                        {'name':'rx',
                         'structure':
                            [{'name':'source_addr', 'len':2},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'rf_data',     'len':None}]},            
                     b"\x89":
                        {'name':'tx_status',
                         'structure':
                            [{'name':'frame_id',    'len':1},
                             {'name':'status',      'len':1}]},
                     b"\x8a":
                        {'name':'status',
                         'structure':
                            [{'name':'status',      'len':1}]},                   
                     }

    def __init__(self, ser, escaped=False):
        self.serial = ser
        self._escaped = escaped

    def _write(self, data):       
        frame = APIFrame(data, self._escaped).output()
        self.serial.write(frame)

    def _wait_for_frame(self):
        frame = APIFrame(escaped=self._escaped)
        while True:
                if self.serial.inWaiting() == 0:
                    time.sleep(.01)
                    continue
                byte = self.serial.read()
                if byte != APIFrame.START_BYTE:
                    continue
                if len(byte) == 1:
                    frame.fill(byte)

                while(frame.remaining_bytes() > 0):
                    byte = self.serial.read()

                    if len(byte) == 1:
                        frame.fill(byte)
                try:                    
                    frame.parse()
                    if len(frame.data) == 0:
                        frame = APIFrame()
                        continue
                    return frame
                except ValueError:                    
                    frame = APIFrame(escaped=self._escaped)

    def _wait_for_frame_for(self, seconds):
        frame = APIFrame(escaped=self._escaped)
        debut = time.time()
        while time.time() <= debut + seconds:
                if self.serial.inWaiting() == 0:
                    time.sleep(.01)
                    continue
                byte = self.serial.read()
                if byte != APIFrame.START_BYTE:
                    continue
                if len(byte) == 1:
                    frame.fill(byte)
                while(frame.remaining_bytes() > 0):
                    byte = self.serial.read()
                    if len(byte) == 1:
                        frame.fill(byte)
                try:                    
                    frame.parse()            
                    if len(frame.data) == 0:
                        frame = APIFrame()
                        continue
                    return frame
                except ValueError:                    
                    frame = APIFrame(escaped=self._escaped)
        return None

    def _build_command(self, cmd, **kwargs):
        try:
            cmd_spec = self.api_commands[cmd]
        except AttributeError:
            raise NotImplementedError("API command specifications could not be found; use a derived class which defines 'api_commands'.")
        packet = b''
        for field in cmd_spec:
            try:            
                data = kwargs[field['name']]
            except KeyError:                
                if field['len'] is not None:                    
                    default_value = field['default']
                    if default_value:                        
                        data = default_value
                    else:                        
                        raise KeyError(
                            "The expected field %s of length %d was not provided"
                            % (field['name'], field['len']))
                else:                    
                    data = None
            if field['len'] and len(data) != field['len']:
                raise ValueError(
                    "The data provided for '%s' was not %d bytes long"\
                    % (field['name'], field['len']))
            if data:
                packet += data
        return packet

    def _split_response(self, data):        
        packet_id = data[0:1]
        try:
            packet = self.api_responses[packet_id]
        except AttributeError:
            raise NotImplementedError("API response specifications could not be found; use a derived class which defines 'api_responses'.")
        except KeyError:            
            for cmd_name, cmd in list(self.api_commands.items()):
                if cmd[0]['default'] == data[0:1]:
                    raise CommandFrameException("Incoming frame with id %s looks like a command frame of type '%s' (these should not be received). Are you sure your devices are in API mode?"
                            % (data[0], cmd_name))
            raise KeyError(
                "Unrecognized response packet with id byte {0}".format(data[0]))
        index = 1
        info = {'id':packet['name']}
        packet_spec = packet['structure']
        for field in packet_spec:
            if field['len'] == 'null_terminated':
                field_data = b''

                while data[index:index+1] != b'\x00':
                    field_data += data[index:index+1]
                    index += 1
                index += 1
                info[field['name']] = field_data
            elif field['len'] is not None:                
                if index + field['len'] > len(data):
                    raise ValueError(
                        "Response packet was shorter than expected")
                field_data = data[index:index + field['len']]
                info[field['name']] = field_data

                index += field['len']            
            else:
                field_data = data[index:]
                if field_data:                    
                    info[field['name']] = field_data
                    index += len(field_data)
                break
        if index < len(data):
            raise ValueError(
                "Response packet was longer than expected; expected: %d, got: %d bytes" % (index, len(data)))        
        if 'parsing' in packet:
            for parse_rule in packet['parsing']:                
                if parse_rule[0] in info:                    
                    info[parse_rule[0]] = parse_rule[1](self, info)
        return info

    def send(self, cmd, **kwargs):
        self._write(self._build_command(cmd, **kwargs))

    def wait_read_frame(self, seconds=0.1):
	frame = self._wait_for_frame_for(seconds)
	if frame is not None:
	        return self._split_response(frame.data)
	return None

    def __getattr__(self, name):    
        if name == 'api_commands':
            raise NotImplementedError("API command specifications could not be found; use a derived class which defines 'api_commands'.")
        if self.shorthand and name in self.api_commands:            
            return lambda **kwargs: self.send(name, **kwargs)
        else:
            raise AttributeError("XBee has no attribute '%s'" % name)