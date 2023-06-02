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
        self.required_pieces_count = []
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
        print("add file", file, "have", have)
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
        if file not in self.count:
            self.count[file] = [0] * (index + 1)
        if index >= len(self.count[file]):
            self.count[file] += [0] * (index - len(self.count[file]) + 1)

        self.count[file][index] += 1 if have else -1
        if (file, index) in self.required_pieces:
            self.rerequire(file, index)

    def update_count_from_bitfield(self, peer_id, peer_bitfield):
        for file, bitfield in peer_bitfield.items():
            for index, have in enumerate(bitfield):
                self.update_count(peer_id, file, index, have)

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
        if file not in self.torrents:
            return
        if not hasattr(self.torrents[file], 'pieces'):
            return
        with open(os.path.join(self.base_dir, file), 'wb') as f:
            for index in range(len(self.torrents[file].pieces)):
                piece = self.read_piece(file, index)
                f.write(piece)

    def rerequire(self, file, index):
        if (file, index) not in self.required_pieces:
            return
        
        with self.lock:
            idx = self.required_pieces.index((file, index))
            self.required_pieces.pop(idx)
            self.required_pieces_count.pop(idx)
            insert(self.required_pieces, self.required_pieces_count, (file, index), self.count[file][index])

    def require(self, file, index):
        with self.lock:
            if (file, index) not in self.required_pieces:
                insert(self.required_pieces, self.required_pieces_count, (file, index), self.count[file][index])

    def require_not(self, file, index):
        with self.lock:
            idx = self.required_pieces.index((file, index))
            self.required_pieces.pop(idx)
            self.required_pieces_count.pop(idx)

    def get_piece_request(self, peer_bitfield, piece_request):
        # find the rarest piece for current peer
        pieces = []
        with self.lock:
            for idx, (file, index) in enumerate(self.required_pieces):
                if peer_bitfield[file][index]:
                    pieces += [(idx, (file, index))]
                    if len(pieces) == 10:
                        break
            
            if len(pieces):
                idx, (piece_request['file'], piece_request['index']) = random.choice(self.required_pieces)

                self.required_pieces.pop(idx)
                self.required_pieces_count.pop(idx)
            else:
                piece_request = None

