import binascii
import json
import socket
import requests

payload_dict = {
  "device": {
    "status": {
      "hexByte": "0a",
      "command": {"gwId": "", "devId": ""}
    },
    "set": {
      "hexByte": "07",
      "command": {"devId": "", "uid": "", "t": ""}
    },
    "prefix": "000055aa00000000000000",    # Next byte is command byte ("hexByte") some zero padding, then length of remaining payload, i.e. command + suffix (unclear if multiple bytes used for length, zero padding implies could be more than one byte)
    "suffix": "000000000000aa55"
  }
}


def hex2bin(x):
    return binascii.unhexlify(x)

def bin2hex(x):
    bin2hex_ret = bytes()
    for idx, val in enumerate(x):
        bin2hex_ret = bin2hex_ret + hex(val,'')
    return bin2hex_ret
    
    
class OutletDevice():
    def __init__(self, dev_id, address, local_key=None, dev_type='device', connection_timeout=5000):
        """
        Represents a Tuya device.

        Args:
            dev_id (str): The device id.
            address (str): The network address.
            local_key (str, optional): The encryption key. Defaults to None.
            dev_type (str, optional): The device type.
                It will be used as key for lookups in payload_dict.
                Defaults to None.

        Attributes:
            port (int): The port to connect to.
        """
        self.id = dev_id
        self.address = address
        self.dev_type = dev_type
        self.connection_timeout = connection_timeout

        self.port = 6668  # default - do not expect caller to pass in

    def get_timestamp(self):
        user_agent = {"user-agent": "curl/7.56.0"}
        return json.loads(requests.get('http://now.httpbin.org', headers=user_agent).content)['now']['epoch']
    
    def __repr__(self):
        return '%r' % ((self.id, self.address),)  # FIXME can do better than this

    def _send_receive(self, payload):
        """
        Send single buffer `payload` and receive a single buffer.
        Args:
            payload(bytes): Data to send.
        """
        try: 
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            s.settimeout(self.connection_timeout)
            s.connect((self.address, self.port))
            
            if(payload != ''):
                s.sendall(payload)
                data, ip = s.recvfrom(1024)
            
        except Exception as e:
            print('error ', e)
        
        s.close()
        return data

    def generate_payload(self, command, data=None):
        """
        Generate the payload to send.

        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to be send.
                This is what will be passed via the 'dps' entry
        """
        
        json_data = payload_dict[self.dev_type][command]['command']
        
        if 'gwId' in json_data:
            json_data['gwId'] = self.id
        if 'devId' in json_data:
            json_data['devId'] = self.id
        if 'uid' in json_data:
            json_data['uid'] = self.id  # still use id, no seperate uid
        if 't' in json_data:
            json_data['t'] = '15998598'

        if data is not None:
            json_data['dps'] = data
            

        # Create byte buffer from hex data
        json_payload = json.dumps(json_data)
        
        
        json_payload = json_payload.replace(' ', '')  # if spaces are not removed device does not respond!
        
        json_payload = bytearray(json_payload)
        
        postfix_payload = hex2bin(bin2hex(json_payload) + payload_dict[self.dev_type]['suffix'])

        #assert len(postfix_payload) <= 0xff
        postfix_payload_hex_len = '%x' % len(postfix_payload)  # TODO this assumes a single byte 0-255 (0x00-0xff)
        buffer = hex2bin( payload_dict[self.dev_type]['prefix'] +
                          payload_dict[self.dev_type][command]['hexByte'] +
                          '000000' +
                          postfix_payload_hex_len ) + postfix_payload
        return buffer

    def status(self):
        # open device, send request, then close connection
        payload = self.generate_payload('status')
        
        data = self._send_receive(payload)
        
        result = data[20:-8]  # hard coded offsets

        result = json.loads(result)

        return result