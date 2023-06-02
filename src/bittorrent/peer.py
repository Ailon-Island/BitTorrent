import os
import time
import datetime
import struct
import bitarray
import random
import threading
from socket import *

from components import *
from piece_manager import PieceManager
from torrent import Torrent
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
    "piece_request": None,
}


class Peer(threading.Thread):
    def __init__(self, name, base_dir="sandbox/peer/1/", host="", port=7889, pieceManager=None):
        super().__init__()

        self.cmd_lock = threading.Lock()
        self.cmd_queue = []
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
        self.busy = True

        self.log(f'[INIT] Peer {self.name} is initialized')

    def cmd(self, msg):
        with self.cmd_lock:
            self.cmd_queue.append(msg)

    def get_cmd(self):
        with self.cmd_lock:
            if len(self.cmd_queue) == 0:
                return None
            return self.cmd_queue.pop(0)

    @staticmethod
    def init_log(name, base_dir, lock):
        log_dir = os.path.join(base_dir, '.logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        log_file = os.path.join(log_dir, f'{name}_{timestamp}.log')

        def log(msg):
            with lock:
                log_fn(msg, log_file)

        return log

    def run(self):
        self.running = True

        self.server.start()

        self.log(f'[START] Peer {self.name} is running on {self.host}:{self.port}')

        self.busy = False
        while self.running:
            self.busy = True

            try:
                cmd_line = self.get_cmd()
                if cmd_line:
                    cmd, *args = cmd_line.split(' ')
                    if cmd in ['bitfield', 'b']:
                        self.log(f'[INFO] The bitfield of peer {self.name} is {self.pieceManager.bitfield}')
                    elif cmd in ['join', 'j']:
                        self.join_network(args[0])
                    elif cmd in ['leave', 'l']:
                        self.leave_network()
                    elif cmd in ['get', 'g', 'download', 'd']:
                        self.download(args[0])
                    elif cmd in ['file', 'f']:
                        for file in args:
                            self.pieceManager.add_file(file)
                    # elif cmd in ['directory', 'dir']:
                    #     for d in args:
                    #         self.pieceManager.add_directory(d)
                    elif cmd in ['quit', 'q']:
                        if self.online:
                            self.leave_network()
                        self.stop()
                        break

                    # if self.online:
                    #     if cmd in ['leave', 'l']:
                    #         self.leave_network()
                    #     elif cmd in ['get', 'g']:
                    #         self.download(args[0])
                    #     elif cmd in ['file', 'f']:
                    #         for file in args:
                    #             self.pieceManager.add_file(file)
                    #     # elif cmd in ['directory', 'dir']:
                    #     #     for d in args:
                    #     #         self.pieceManager.add_directory(d)
                    #     elif cmd in ['quit', 'q']:
                    #         self.leave_network()
                    #         self.stop()
                    #         break
                    # else:
                    #     if cmd in ['join', 'j']:
                    #         self.join_network(args[0])
                    #     elif cmd in ['quit', 'q']:
                    #         self.stop()
                    #         break
                    #     elif not self.running and len(self.peerConnections) == 0:
                    #         break
                    self.busy = False
                else:
                    self.busy = False
                    time.sleep(0.01)
            except Exception as e:
                self.log("[ERROR] Peer get exception:", type(e).__name__)
                self.busy = False

        self.cleanup()
        self.log(f'[STOP] Peer {self.name} stopped')

    def cleanup(self):
        self.busy = True
        if self.online:
            self.leave_network()
        self.log('[STOP] Stopping server...')
        self.server.stop()
        self.server.join()
        self.log('[STOP] Server stopped')

    def join_network(self, torrent_file):
        if self.online:
            self.log(f'[WARN] Peer {self.name} is already online, if you want to join another network, please leave first')
            return
        if not os.path.exists(os.path.join(self.base_dir, torrent_file)):
            self.log(f'[ERROR] Torrent file {torrent_file} does not exist')
            return

        torrent = Torrent()
        torrent.read_torrent(os.path.join(self.base_dir, torrent_file))

        self.tracker_host = torrent.announce
        self.tracker_port = torrent.port

        try:
            connectRequest = self.make_request("started")
            self.trackerConnection = Client(self.tracker_host, self.tracker_port)
            self.trackerConnection.send_file(connectRequest, self.connect_all)
            self.trackerConnection.start()
            self.online = True
        except Exception as e:
            self.trackerConnection = None

            self.log(f'[ERROR] Failed to connect to tracker: {e}')
            return

        self.log(f'[JOIN] Peer {self.name} has joined the network with host {self.tracker_host} and port {self.tracker_port}')

        for torrent in self.pieceManager.torrents.values():
            torrent.write_torrent(dir=os.path.join(self.base_dir, '.torrents'), announce=self.tracker_host, port=self.tracker_port)

        self.online = True

    def leave_network(self):
        if not self.online:
            self.log(f'[WARN] Peer {self.name} attempted to leave the network, but it has not joined any network yet')
            return
        self.log(f'[LEAVE] Peer {self.name} is leaving the network...')


        try:
            connectRequest = self.make_request("stopped")
            self.trackerConnection.send_file(connectRequest)
            # self.log(f'[LEAVE] Peer {self.name} is sending a leave request to the tracker')
            while self.trackerConnection.busy:
                time.sleep(0.01)
            self.trackerConnection.stop()
            self.trackerConnection.join()
            self.trackerConnection = None
            self.online = False
        except Exception as e:
            self.log(f'[ERROR] Failed to communicate with tracker: {type(e).__name__}')

        self.log(f'[LEAVE] Peer {self.name} has left the network')

    def stop(self):
        self.running = False

    def download(self, torrent_file):
        if not self.online:
            self.join_network(torrent_file)

        if not os.path.exists(os.path.join(self.base_dir, torrent_file)):
            self.log(f'[ERROR] Torrent file {torrent_file} does not exist')
            return

        torrent = Torrent()
        torrent.read_torrent(os.path.join(self.base_dir, torrent_file))

        self.pieceManager.add_file(torrent=torrent)

        # self.log(f'[JOIN] Peer {self.name} is downloading {torrent_file.split("/")[-1].split(".")[:-1].join(".")}')

    def connect_all(self, file, connectionSocket):
        if file['error_code'] != 0:
            raise Exception(f'Error code {file["error_code"]}: {file["message"]}')

        self.log(f'[INFO] Peer {self.name} is connecting to {file["num-of-peers"]} peers')
        message = self.make_message("Bitfield")
        for peer in file['peers'].values():
            message['ip'] = peer['ip']
            message['port'] = peer['port']
            message['peer_id'] = peer['peer_id']
            connection = PeerClient(peer['peer_id'], peer['ip'], peer['port'], recv_fn=self.serve, states=INIT_STATES)
            connection.set_server(message)
            connection.start()
            self.peerConnections[peer['peer_id']] = connection
            self.log(f'[INFO] Peer {self.name} connected to {peer["peer_id"]}')

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
        if message.get('type') != "KeepAlive":
            self.log(f'[SERVE] Peer {self.name} received message {message} from {peer_id}')

        if not self.online:
            response = self.make_message("ServerClose")
            self.peerConnections.pop(peer_id)
            return response, True

        # deal with the message
        type = message['type'] if 'type' in message else None
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
        elif type == "Bitfield":
            states['peer_bitfield'] = {k: bitarray.bitarray(bf) for k, bf in message['bitfield'].items()}
            self.pieceManager.update_count_from_bitfield(peer_id, states['peer_bitfield'])
        elif type == "Request":
            pass
        elif type == "Piece":
            if states['piece_request'] is None or message['file'] != states['piece_request']['file'] or message['index'] != states['piece_request']['index']:
                pass
            if not self.pieceManager.write_piece(message['file'], message['index'], message['piece']):
                self.log(f'[ERROR] Peer {self.name} failed to write piece {message["index"]} of file {message["file"]}')
                self.pieceManager.require(states['piece_request']['file'], states['piece_request']['index'])
            states['piece_request'] = None
        elif type == "ServerClose":
            self.peerConnections.pop(peer_id)
        elif message['len'] == 0: # keep alive
            pass
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
            piece = self.pieceManager.read_piece(message['file'], message['index'])
            response = self.make_message("Piece", file=message['file'], index=message['index'], piece=piece)
        elif not states['recv']['choke'] and states['recv']['interested']:  # peer unchoke, my interested
            if states['piece_request'] is None:
                states['piece_request'] = self.pieceManager.get_piece_request(states['peer_bitfield'])
            if states['piece_request'] is not None:
                response = self.make_message("Request", file=states['piece_request']['file'], index=states['piece_request']['index'])
            else:
                response = self.make_message("UnInterested")
        elif states['recv']['choke'] and not states['recv']['interested']:  # peer choke, my uninterested
            if states['piece_request'] is not None:
                self.pieceManager.require(states['piece_request']['file'], states['piece_request']['index'])
            states['piece_request'] = self.pieceManager.get_piece_request(states['peer_bitfield'])
            if states['piece_request'] is not None:
                self.log(f'[INFO] Peer {self.name} is requesting piece {states["piece_request"]} from {peer_id}')
                states['recv']['interested'] = True
                response = self.make_message("Interested")

        return response, stop

    def connected(self, message, connectionSocket):
        self.log(f'[INFO] Peer {self.name} is connected by {message["peer_id"]}')
        connection = PeerClient(message['peer_id'], message['ip'], message['port'], recv_fn=self.serve, states=INIT_STATES)
        response, _ = self.serve(message['peer_id'], message, connectionSocket, states=connection.states, new=True)
        self.log(f'[INFO] Peer {self.name} sent message {response} to {message["peer_id"]}')
        connection.set_server(response, socket=connectionSocket)
        connection.start()
        self.peerConnections[message['peer_id']] = connection

        return response

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
            message['bitfield'] = {k: bf.tolist() for k, bf in self.pieceManager.bitfield.items()}
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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Peer')
    parser.add_argument('-N', '--name', type=str, default='peer', help='Name of the peer')
    parser.add_argument('-D', '--dir', type=str, default='.', help='Directory to store files')
    parser.add_argument('-H', '--host', type=str, default='', help='Host of the peer')
    parser.add_argument('-P', '--port', type=int, default=0, help='Port of the peer')
    args = parser.parse_args()

    peer = Peer(args.name, args.dir, args.host, args.port)
    peer.start()

    while True:
        try:
            if peer.running:
                if not peer.busy:
                    line = input("Please enter command: ")
                    peer.cmd(line)
                    time.sleep(0.03)
                else:
                    time.sleep(0.1)
            else:
                break
        except KeyboardInterrupt:
            print('\n[INFO] Keyboard Interrupt')
            peer.stop()
            break

    print('[INFO] Waiting for program to exit')
    peer.join()
    print('[INFO] Program exited')


