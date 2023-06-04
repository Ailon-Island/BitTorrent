from collections.abc import Callable
import json
import base64
from struct import pack, unpack
import socket
import bisect
from typing import Any


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return "BYTES" + base64.b64encode(obj).decode('utf-8')
        return json.JSONEncoder.default(self, obj)
    

class MyDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self._object_hook, *args, **kwargs)

    def _object_hook(self, dct):
        for key, value in dct.items():
            if isinstance(value, str) and value.startswith('BYTES'):
                try:
                    dct[key] = base64.b64decode(value[5:])
                except UnicodeEncodeError:
                    pass 
        return dct


def obj_encode(obj):
    return json.dumps(obj, cls=MyEncoder, indent=4, sort_keys=True, separators=(',', ':')).encode('utf-8')


def obj_decode(binary):
    return json.loads(binary.decode('utf-8'), cls=MyDecoder)


def binary2json(binary):
    obj = obj_decode(binary)
    return json.dumps(obj, cls=MyEncoder, indent=4, sort_keys=True)


def obj2json(obj):
    return json.dumps(obj, cls=MyEncoder, indent=4, sort_keys=True)


def log_fn(msg, log_file=None):
    print(msg)
    if log_file:
        with open(log_file, 'a') as f:
            f.write(msg + '\n')


def insert(seq, keys, item, key):
    idx = bisect.bisect_left(keys, key)
    keys.insert(idx, key)  
    seq.insert(idx, item)
