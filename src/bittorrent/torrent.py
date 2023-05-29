# torrent file parser: convert a file into a .torrent metafile, and vice versa
import os
import json
import hashlib
import socket
from utils import *

class Torrent:
    def __init__(self, announce=None, port=None, piece_len=4096):
        self.torrent = {
            'announce': announce,
            'port': port,
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
        return self.torrent['announce']

    @announce.setter
    def announce(self, announce):
        self.torrent['announce'] = announce

    @property
    def port(self):
        return self.torrent['port']

    @port.setter
    def port(self, port):
        self.torrent['port'] = port

    @property
    def comment(self):
        return self.torrent['comment']

    @comment.setter
    def comment(self, comment):
        self.torrent['comment'] = comment

    @property
    def info(self):
        return self.torrent['info']

    @info.setter
    def info(self, info):
        self.torrent['info'] = info

    def make_torrent(self, file, file_name, file_dir, ):
        self.info['name'] = os.path.basename(file_name)
        self.info['length'] = os.path.getsize(file_name)
        # hash the file into pieces
        with open(file_name, 'rb') as f:
            while True:
                piece = f.read(self.piece_len)
                if not piece:
                    break
                # need to convert to string, otherwise not JSON serializable
                self.info['pieces'].append(str(hashlib.sha1(piece).digest()))
    
    def write_torrent(self, dir=None, announce=None, port=None, comment=None):
        # record the torrent file information
        dir = dir or os.getcwd()
        file = os.path.join(dir, self.info['name'].split('.')[-2] + '.torrent')
        torrent = self.torrent
        torrent['announce'] = announce or self.announce
        torrent['port'] = port or self.port
        torrent['comment'] = comment or self.comment
        if os.path.exists(file) and announce is None and port is None and comment is None:
            print(f'File {file} already exists, please specify a new file name')
            return
        with open(file, 'w') as f:
            json.dump(torrent, f, indent=4)
    
    # read .torrent file and load json information
    def read_torrent(self, torrent_file):
        with open(torrent_file, 'r') as f:
            torrent = json.load(f)
        self.torrent = torrent
    
    def compare_file(self, download_file):
        # torrent_file = self.read_torrent(torrent_file_name)
        piece_length = self.info['piece_length']
        
        # first check whether the file size is the same
        if os.path.getsize(download_file) != self.info['length']:
            raise Exception('File size does not match')
        
        # then check whether the file is the same
        piece_num = len(self.info['pieces'])
        bit_map = [0] * piece_num # 0 means not checked(or check failure), 1 means check success
        valid = True
        piece_index = 0
        with open(download_file, 'rb') as f:
            while True:
                piece = f.read(piece_length)
                if not piece:
                    break
                if str(hashlib.sha1(piece).digest()) == self.info['pieces'][piece_index]:
                    bit_map[piece_index] = 1
                else:
                    valid = False
                piece_index += 1
        return valid, bit_map
    
    def compare_piece(self, index, piece):
        return str(hashlib.sha1(piece).digest()) == self.info['pieces'][index]

if __name__ == "__main__":
    torrent=Torrent()
    download_file = 'test.txt'
    torrent_file_name = 'test.torrent'
    torrent.make_torrent(download_file, download_file, '.')
    print(torrent.compare_file(download_file))