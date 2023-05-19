import json
from struct import pack, unpack
import socket


def obj_encode(obj):
    return json.dumps(obj, indent=4, sort_keys=True, separators=(',', ':')).encode('utf-8')


def obj_decode(binary):
    return json.loads(binary.decode('utf-8'))


def binary2json(binary):
    obj = obj_decode(binary)
    return json.dumps(obj, indent=4, sort_keys=True)


def obj2json(obj):
    return json.dumps(obj, indent=4, sort_keys=True)


def log_fn(msg, log_file=None):
    print(msg)
    if log_file:
        with open(log_file, 'a') as f:
            f.write(msg + '\n')


