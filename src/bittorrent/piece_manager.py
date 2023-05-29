import os
import random
import collections
import bisect
import bitarray
import hashlib
import threading

from utils import *
from torrent import *


class PieceManager:
    def __init__(self, base_dir="", piece_len=4096, piece_buffer_size=1024*1024):
        """
        A piece manager that manages the pieces of files
        :param base_dir:
        :param piece_len:
        :param piece_buffer_size:


        The piece manager does not manage any files or directories at initialization.

        Each file takes an item in the dict `bitfield`. The key is the file name appended with the md5 hash sum of the
        file, and the value is the bitarray bitfield of the file.

        For memory-performance balance, LRU or a certain other strategy is used. Pieces in memory are stored in a
        dictionary `piece_buffer`, while pieces on disk are stored in a folder [base_dir]/.pieces.

        To facilitate rarest-first downloading, the piece manager maintains a dictionary `count` that maps each piece
        to the number of peers that have that piece.

        `required_pieces` is a list of pieces that are required by the client. When a piece is required to be
        downloaded, it is added to `required_pieces`. When a piece is (ready to be) downloaded, it will be removed then.

        Since multiple threads would operate piece manager, `lock` shall be used on modification.
        """
        self.base_dir = base_dir
        self.pieces_folder = os.path.join(base_dir, ".pieces")
        self.torrents = {}
        self.piece_len = piece_len
        self.bitfield = {}
        self.torrents = {}
        self.count = {}
        self.piece_buffer_size = piece_buffer_size
        self.piece_buffer = collections.OrderedDict()
        # self.hashes = {}
        self.required_pieces = []
        self.lock = threading.Lock()

        self.init()

    def init(self):
        if not os.path.exists(self.pieces_folder):
            os.mkdir(self.pieces_folder)

        for item in os.listdir(self.base_dir):
            if item.startswith('.'):
                continue
            # if os.path.isdir(os.path.join(self.base_dir, item)):
            #     self.add_directory(item)
            # else:
            self.add_file(file=item, have=True)

    def add_file(self, file=None, torrent=None, have=False):
        if have:
            torrent = Torrent(self.piece_len)
            torrent.make_torrent(file, os.path.join(self.base_dir, file), self.base_dir)
        else: # not have
            file = torrent.info['name']

        if file in self.torrents:
            self.torrents[file].info['pieces'] = torrent.info['pieces']
            return
        
        self.torrents[file] = torrent
        self.bitfield[file] = bitarray.bitarray(len(torrent.info['pieces']))
        self.bitfield[file].setall(have)
        self.count[file] = [0] * len(torrent.info['pieces'])

        if have:
            with open(os.path.join(self.base_dir, file), 'rb') as f:
                index = 0
                while True:
                    piece = f.read(self.piece_len)
                    if not piece:
                        break
                    self.write_piece(file, index, piece)
                    index += 1

    def add_directory(self, directory):
        pass

    def update_count(self, peer_id, file, index, have):
        self.count[file][index] += 1 if have else -1
        if (file, index) in self.required_pieces:
            self.rerequire(file, index)

    def read_piece(self, file, index):
        if file not in self.bitfield or not self.bitfield[file][index]:
            return None
        if (file, index) in self.piece_buffer:
            self.piece_buffer.move_to_end((file, index))
            return self.piece_buffer[(file, index)]
        
        with open(os.path.join(self.pieces_folder, file + "." + str(index)), 'rb') as f:
            piece = f.read()
            self.piece_buffer[(file, index)] = piece
            if len(self.piece_buffer) > self.piece_buffer_size:
                self.piece_buffer.popitem(last=False)

    def write_piece(self, file, index, piece):
        if not self.torrents[file].compare_piece(index, piece):
            return False

        with open(os.path.join(self.pieces_folder, file + "." + str(index)), 'wb') as f:
            f.write(piece)
        self.bitfield[file][index] = True
        
        if self.bitfield[file].all():
            self.archive_file(file)

        return True
    
    def archive_file(self, file):
        with open(os.path.join(self.base_dir, file), 'wb') as f:
            for index in range(len(self.torrents[file].pieces)):
                piece = self.read_piece(file, index)
                f.write(piece)

    def rerequire(self, file, index):
        if (file, index) not in self.required_pieces:
            return
        
        with self.lock:
            self.required_pieces.remove((file, index))
            bisect.insort(self.required_pieces, (file, index), key=lambda p: self.count[p[0]][p[1]])

    def require(self, file, index):
        with self.lock:
            if (file, index) not in self.required_pieces:
                bisect.insort(self.required_pieces, (file, index), key=lambda p: self.count[p[0]][p[1]])

    def require_not(self, file, index):
        with self.lock:
            self.required_pieces.remove((file, index))

    def get_piece_request(self, peer_bitfield, piece_request):
        # find the rarest piece for current peer
        pieces = []
        with self.lock:
            for file, index in self.required_pieces:
                if peer_bitfield[file][index]:
                    pieces += [(file, index)]
                    if len(pieces) == 10:
                        break
            
            if len(pieces):
                piece_request['file'], piece_request['index'] = random.choice(self.required_pieces)

                self.required_pieces.remove((piece_request['file'], piece_request['index']))
            else:
                piece_request = None

