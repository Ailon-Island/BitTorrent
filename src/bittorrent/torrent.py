# torrent file parser: convert a file into a .torrent metafile, and vice versa
import os
import json
import hashlib
import socket
from utils import *

class Torrent:
    def __init__(self, piece_len=4096):
        self.file = {
            'announce': None,
            'port': None,
            'comment': "",
            'info': {
                'name': None,
                'length': None,
                'piece_length': piece_len,
                'pieces': []
            }
        }

        self.piece_len = piece_len

    @property
    def announce(self):
        return self.file['announce']

    @announce.setter
    def announce(self, announce):
        self.file['announce'] = announce

    @property
    def port(self):
        return self.file['port']

    @port.setter
    def port(self, port):
        self.file['port'] = port

    @property
    def comment(self):
        return self.file['comment']

    @comment.setter
    def comment(self, comment):
        self.file['comment'] = comment

    @property
    def info(self):
        return self.file['info']

    @info.setter
    def info(self, info):
        self.file['info'] = info

    def add_file(self, file, file_name, file_dir):
        self.file['info']['name'] = os.path.basename(file_name)
        self.file['info']['length'] = os.path.getsize(file_name)
        # hash the file into pieces
        with open(file_name, 'rb') as f:
            while True:
                piece = f.read(self.piece_len)
                if not piece:
                    break
                # need to convert to string, otherwise not JSON serializable
                self.file['info']['pieces'].append(str(hashlib.sha1(piece).digest()))
        # record the torrent file information
        with open(self.file['info']['name'].split('.')[-2] + '.torrent', 'w') as f:
            json.dump(self.file, f, indent=4)
    
    # read .torrent file and load json information
    def read_torrent(self, torrent_file):
        with open(torrent_file, 'r') as f:
            torrent = json.load(f)
        return torrent
    def compare_file(self, torrent_file_name, download_file):
        torrent_file = self.read_torrent(torrent_file_name)
        piece_length = torrent_file['info']['piece_length']
        
        # first check whether the file size is the same
        if os.path.getsize(download_file) != torrent_file['info']['length']:
            raise Exception('File size does not match')
        
        # then check whether the file is the same
        piece_num = len(torrent_file['info']['pieces'])
        bit_map = [0] * piece_num # 0 means not checked(or check failure), 1 means check success
        valid = True
        piece_index = 0
        with open(download_file, 'rb') as f:
            while True:
                piece = f.read(piece_length)
                if not piece:
                    break
                if str(hashlib.sha1(piece).digest()) == torrent_file['info']['pieces'][piece_index]:
                    bit_map[piece_index] = 1
                else:
                    valid = False
                piece_index += 1
        return valid, bit_map

if __name__ == "__main__":
    torrent=Torrent()
    download_file = 'test.txt'
    torrent_file_name = 'test.torrent'
    torrent.add_file('', 'test.txt', '')
    print(torrent.compare_file(torrent_file_name, download_file))