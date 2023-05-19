import os
import datetime
import threading
from socket import *

from components import *
from utils import *


class Peer:
    def __init__(self, name, torrent_file, folder="", host="", port=7889):
        self.name = name
        self.folder = folder
        self.log_dir = os.path.join(folder, 'log')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.log_file = os.path.join(self.log_dir, f'{name}_{timestamp}.log')
        self.log = lambda msg: self.log_fn(msg, self.log_file)
        self.host = host
        self.port = port
        self.torrent = None
        self.tracker_host = None
        self.tracker_port = None
        self.tracker = None
        self.bitField = {}
        self.server = Server(host, port, self.connected)
        self.peerConnections = {}

        self.log(f'[INIT] Peer {self.name} is initialized')

        self.join_network(torrent_file)

    def join_network(self, torrent_file):
        if not os.path.exists(torrent_file):
            self.log(f'[ERROR] Torrent file {torrent_file} does not exist')
            return

        with open(torrent_file, 'r') as f:
            torrent = json.load(f)

            self.torrent = torrent
            self.tracker_host = torrent['announce']
            self.tracker_port = torrent['port']
            file_info = torrent['info']
            self.bitField = [0] * (file_info['length'] // file_info['piece length'] + 1)

        self.log(f'[JOIN] Peer {self.name} has joined the network with host {self.tracker_host} and port {self.tracker_port}')




    def start(self):
        pass

    def connect(self, peer_host, peer_port):
        pass

    def connected(self, file, connectionSocket):
        pass


