import os
import collections
import bisect
import bitarray
import hashlib
import threading

from ..utils import *


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
        self.piece_len = piece_len
        self.bitfield = {}
        self.count = {}
        self.piece_buffer_size = piece_buffer_size
        self.piece_buffer = []
        self.hashes = {}
        self.required_pieces = []
        self.lock = threading.Lock()

    def add_file(self, file):
        pass

    def add_directory(self, directory):
        pass

    def update_count(self, peer_id, file, index, have):
        pass

    def read_piece(self, file, index):
        pass

    def write_piece(self, file, index, piece):
        pass

    def require(self, file, index):
        pass

    def require_not(self, file, index):
        pass


