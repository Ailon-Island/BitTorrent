import json
import socket


def objEncode(obj):
    return json.dumps(obj,indent=4, sort_keys=True,separators=(',',':')).encode('utf-8')

def objDecode(binary):
    return json.loads(binary.decode('utf-8'))

def binary_to_beautiful_json(binary):
    obj = objDecode(binary)
    return json.dumps(obj,indent=4, sort_keys=True)

def obj_to_beautiful_json(obj):
    return json.dumps(obj,indent=4, sort_keys=True)