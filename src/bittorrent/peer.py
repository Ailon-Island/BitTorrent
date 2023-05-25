import os
import datetime
import threading
from socket import *

from components import *
from .piece_manager import PieceManager
from utils import *

INIT_STATES = {
    "send": {
        "choke": True,
        "interested": False,
    },
    "recv": {
        "choke": True,
        "interested": False,
    },
    "peer_bitfield": None,
    "piece_request": {
        "file": None,
        "index": None,
    }
}


class Peer(threading.Thread):
    def __init__(self, name, base_dir="sandbox/peer/1/", host="", port=7889, pieceManager=None):
        self.name = name
        self.base_dir = base_dir
        self.log_lock = threading.Lock()
        self.log = self.init_log(name, base_dir, self.log_lock)
        self.online = False
        self.host = host
        self.port = port
        self.tracker_host = None
        self.tracker_port = None
        self.trackerConnection = None
        self.pieceManager = pieceManager if pieceManager else PieceManager(base_dir)
        self.server = Server(host, port, self.connected)
        self.peerConnections = {}
        self.running = False

        self.log(f'[INIT] Peer {self.name} is initialized')

    @staticmethod
    def init_log(name, base_dir, lock):
        log_dir = os.path.join(base_dir, 'log')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        log_file = os.path.join(log_dir, f'{name}_{timestamp}.log')

        def log(msg):
            with lock:
                log_fn(msg, log_file)

        return log

    def run(self):
        self.running = True

        self.server.start()

        self.log(f'[START] Peer {self.name} is running on {self.host}:{self.port}')

        while self.running:
            if self.online:
                line = input("Please enter a command: ")
                cmd, *args = line.split(' ')
                if cmd in ['join', 'j']:
                    self.join_network(args[0])
                elif cmd in ['leave', 'l']:
                    self.leave_network()
                elif cmd in ['get', 'g']:
                    self.download(args[0])
                elif cmd in ['file', 'f']:
                    for file in args:
                        self.pieceManager.add_file(file)
                elif cmd in ['directory', 'dir']:
                    for d in args:
                        self.pieceManager.add_directory(d)
                elif cmd in ['quit', 'q']:
                    self.quit()
            else:
                if len(self.peerConnections) == 0:
                    break

    def join_network(self, torrent_file):
        if not os.path.exists(torrent_file):
            self.log(f'[ERROR] Torrent file {torrent_file} does not exist')
            return

        with open(torrent_file, 'r') as f:
            torrent = json.load(f)

        self.tracker_host = torrent['announce']
        self.tracker_port = torrent['port']

        try:
            connectRequest = self.make_request("started")
            self.trackerConnection = Client(self.tracker_host, self.tracker_port, recv_fn=self.connect_all)
            self.trackerConnection.set_file(connectRequest)
            self.trackerConnection.start()
            self.trackerConnection.join()
            self.online = True
        except Exception as e:
            self.trackerConnection = None

            self.log(f'[ERROR] Failed to connect to tracker: {e}')
            return

        self.log(f'[JOIN] Peer {self.name} has joined the network with host {self.tracker_host} and port {self.tracker_port}')

    def leave_network(self):
        if not self.online:
            self.log(f'[WARN] Peer {self.name} attempted to leave the network, but it has not joined any network yet')
            return

        try:
            connectRequest = self.make_request("stopped")
            self.trackerConnection.set_file(connectRequest)
            self.trackerConnection.start()
            self.trackerConnection.join()
            self.trackerConnection = None
            self.online = False
        except Exception as e:
            self.log(f'[ERROR] Failed to connect to tracker: {e}')

        self.log(f'[LEAVE] Peer {self.name} has left the network')

    def quit(self):
        if self.online:
            self.leave_network()
        self.server.stop()
        self.running = False

    def download(self, torrent_file):
        pass

    def connect_all(self, file, connectionSocket):
        if file['error_code'] != 0:
            raise Exception(f'Error code {file["error_code"]}: {file["message"]}')

        message = self.make_message("Bitfield")
        for peer in file['peers'].values():
            message['ip'] = peer['ip']
            message['port'] = peer['port']
            message['peer_id'] = peer['peer_id']
            connection = PeerClient(peer['peer_id'], peer['ip'], peer['port'], recv_fn=self.serve, states=INIT_STATES)
            connection.set_server(message)
            connection.start()
            self.peerConnections[peer['peer_id']] = connection

    def serve(self, peer_id, message, connectionSocket, states, new=False):
        """
        Serve a peer's message
        :param peer_id:
        :param message:
        :param connectionSocket:
        :param states:
        :param new:
        :return:
        :file:
        :stop:
        """
        if not self.online:
            response = self.make_message("ServerClose")
            self.peerConnections.pop(peer_id)
            return response, True

        # deal with the message
        type = message['type']
        stop = False
        if type == "Choke":
            states['recv']['choke'] = True
        elif type == "UnChoke":
            states['recv']['choke'] = False
        elif type == "Interested":
            states['send']['interested'] = True
        elif type == "UnInterested":
            states['send']['interested'] = False
        elif type == "Have":
            states['peer_bitfield'][message['file']][message['index']] = message['have']
            self.pieceManager.update_count(peer_id, message['file'], message['index'], message['have'])
        elif type == "Request":
            pass
        elif type == "Piece":
            if not self.pieceManager.write_piece(message['file'], message['index'], message['piece']):
                self.drop_request(states['piece_request'])
            states['piece_request'] = None
        elif type == "ServerClose":
            self.peerConnections.pop(peer_id)
        else:
            raise Exception(f'Invalid message type {type}')

        # make response
        response = self.make_message("KeepAlive")
        if type == "Bitfield" and new:
            response = self.make_message("Bitfield")
        elif type == "ServerClose":
            response = self.make_message("ServerClose")
            stop = True
        elif type == "UnInterested":
            states['send']['choke'] = True
            response = self.make_message("Choke")
        elif type == "Interested":
            states['send']['choke'] = False
            response = self.make_message("UnChoke")
        elif type == "Request" and not states['send']['choke'] and states['send']['interested']:
            piece = self.pieceManager.read(message['file'], message['index'])
            response = self.make_message("Piece", file=message['file'], index=message['index'], piece=piece)
        elif not states['recv']['choke'] and states['recv']['interested']:
            if states['piece_request'] is None:
                self.get_piece_request(states['peer_bitfield'], states['piece_request'])
            if states['piece_request'] is not None:
                response = self.make_message("Request", file=states['piece_request']['file'], index=states['piece_request']['index'])
            else:
                response = self.make_message("UnInterested")
        elif states['recv']['choke'] and not states['recv']['interested']:
            if states['piece_request'] is not None:
                self.drop_request(states['piece_request'])
            self.get_piece_request(states['peer_bitfield'], states['piece_request'])
            if states['piece_request'] is not None:
                response = self.make_message("Interested")

        return response, stop

    def connected(self, message, connectionSocket):
        connection = PeerClient(message['peer_id'], message['ip'], message['port'], recv_fn=self.serve, states=INIT_STATES)
        response = self.serve(message, connectionSocket, states=connection.states, new=True)
        connection.set_server(response, socket=connectionSocket)
        connection.start()
        self.peerConnections[message['peer_id']] = connection

    def make_request(self, event="started"):
        request = {
            'port': self.port,
            'ip': self.host,
            'peer_id': f"{self.host}:{self.port}",
            'event': event,
        }

        return request

    def make_message(self, type="Bitfield", **kwargs):
        message = {
            'type': type,
        }

        if type == "Choke":
            message['len'] = 1
            message['id'] = 0
        elif type == "UnChoke":
            message['len'] = 1
            message['id'] = 1
        elif type == "Interested":
            message['len'] = 1
            message['id'] = 2
        elif type == "UnInterested":
            message['len'] = 1
            message['id'] = 3
        elif type == "Have":
            message['len'] = 6
            message['id'] = 4
            message['have'] = kwargs['have']
            message['file'] = kwargs['file']
            message['index'] = kwargs['index']
        elif type == "Bitfield":
            message['len'] = 1 + len(self.pieceManager.bitfield)
            message['id'] = 5
            message['bitfield'] = self.pieceManager.bitfield
        elif type == "Request":
            message['len'] = 13
            message['id'] = 6
            message['file'] = kwargs['file']
            message['index'] = kwargs['index']
        elif type == "Piece":
            message['len'] = 9 + len(kwargs['piece'])
            message['id'] = 7
            message['file'] = kwargs['file']
            message['index'] = kwargs['index']
            message['piece'] = kwargs['piece']
        elif type == "KeepAlive":
            message['len'] = 0
        elif type == "ServerClose":
            message['len'] = 1
            message['id'] = 8
        else:
            raise Exception(f'Invalid message type {type}')

        return message

    def get_piece_request(self, peer_bitfield, piece_request):
        # find the rarest piece for current peer
        rarest_count = len(self.peerConnections) + 1
        for file, index in self.pieceManager.required_pieces:
            if peer_bitfield[file][index] == 1:
                count = self.pieceManager.count[file][index]
                if count < rarest_count:
                    piece_request['file'], piece_request['index'] = file, index
                    rarest_count = count

        self.pieceManager.require_not(piece_request['file'], piece_request['index'])

    def drop_piece_request(self, piece_request):
        self.pieceManager.require(piece_request['file'], piece_request['index'])

