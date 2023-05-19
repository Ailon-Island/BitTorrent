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
        self.trackerConnection = None
        self.bitField = {}
        self.bitFields = {}
        self.server = Server(host, port, self.connected)
        self.peerConnections = {}

        self.log(f'[INIT] Peer {self.name} is initialized')

    def join_network(self, torrent_file):
        if not os.path.exists(torrent_file):
            self.log(f'[ERROR] Torrent file {torrent_file} does not exist')
            return

        with open(torrent_file, 'r') as f:
            torrent = json.load(f)

            self.torrent = torrent
            self.tracker_host = torrent['announce']
            self.tracker_port = torrent['port']

            try:
                connectRequest = self.make_request("started")
                self.trackerConnection = Client(self.tracker_host, self.tracker_port)
                self.trackerConnection.send(connectRequest, recv_fn=self.connect_all)
            except Exception as e:
                self.log(f'[ERROR] Failed to connect to tracker: {e}')
                return

        self.log(f'[JOIN] Peer {self.name} has joined the network with host {self.tracker_host} and port {self.tracker_port}')

    def download(self, torrent_file):
        pass

    def connect_all(self, file, connectionSocket):
        if file['error_code'] != 0:
            raise Exception(f'Error code {file["error_code"]}: {file["message"]}')

        connectMessage = self.make_message("Bitfield")
        for peer in file['peers'].values():
            connection = Client(peer['ip'], peer['port'])
            connection.send_peer(connectMessage)

    def connect(self, file, connectionSocket):
        pass

    def connected(self, file, connectionSocket):
        pass

    def make_request(self, event="started"):
        request = {
            'port': self.port,
            'ip': self.host,
            'peer_id': f"{self.host}:{self.port}",
            'event': event,
        }

        return request

    def make_message(self, type="Bitfield"):
        message = {
            'type': type,
        }

        if type == "Choke":
            pass
        elif type == "UnChoke":
            pass
        elif type == "Interested":
            pass
        elif type == "UnInterested":
            pass
        elif type == "Have":
            pass
        elif type == "Bitfield":
            message['length'] = len(self.bitField)
            message['bitfield'] = self.bitField
            message['message_id'] = 5
        elif type == "Request":
            pass
        elif type == "Piece":
            pass
        elif type == "KeepAlive":
            pass
        elif type == "ServerClose":
            pass
        else:
            raise Exception(f'Invalid message type {type}')

        return message
