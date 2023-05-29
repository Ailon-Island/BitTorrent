import os
import datetime
import threading
from socket import *

from components import *
from utils import *


class Tracker(threading.Thread):
    def __init__(self, name, base_dir="sandbox/tracker/", host="", port=7889):
        self.name = name
        self.dir = base_dir
        self.log_lock = threading.Lock()
        self.log = self.init_log(name, base_dir, self.log_lock)
        self.host = host
        self.port = port
        self.peers = {}
        self.server = Server(host, port, self.respond)

        self.log(f'[INIT] Tracker {self.name} is initialized')

    @staticmethod
    def init_log(name, base_dir, lock):
        log_dir = os.path.join(base_dir, '.logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        log_file = os.path.join(log_dir, f'{name}_{timestamp}.log')

        def log(msg):
            with lock:
                log_fn(msg, log_file)

        return log

    def run(self):
        self.server.start()

        self.log(f'[START] Tracker {self.name} is running on {self.host}:{self.port}')

        while True:
            cmd = input('Enter command: ')
            if cmd in ['quit', 'q']:
                break

    
    def respond(self, request, connectionSocket):
        self.log(f'[REQUEST] Received request: {request}')

        response = {
            'error_code': 0,
            'message': None,
            'num-of-peers': len(self.peers),
            'peers': self.peers.copy()
        }

        event = request['event']
        if event == 'started':
            if request['peer_id'] not in self.peers:
                peer = {
                    'ip': request['ip'],
                    'port': request['port'],
                    'peer_id': request['peer_id']
                }
                self.peers[request['peer_id']] = peer

                response['message'] = 'You\'ve joined! Welcome to the P2P network!'

                self.log(f'Peer {request["peer_id"]} joined the network!')
            else:
                response['error_code'] = 1
                response['message'] = 'You\'re already in the network!'
                response['num-of-peers'] = None
                response['peers'] = None

                self.log(f'Peer {request["peer_id"]} requested to join the network, but it is already in the network!')

        elif event == 'completed':
            if request['peer_id'] in self.peers:
                self.peers.pop(request['peer_id'])

                response['message'] = 'You\'ve left! Goodbye!'

                self.log(f'Peer {request["peer_id"]} left the network!')
            else:
                response['error_code'] = 1
                response['message'] = 'You\'re not in the network!'
                response['num-of-peers'] = None
                response['peers'] = None

                self.log(f'Peer {request["peer_id"]} requested to leave the network, but it is not in the network!')

        else:
            response['error_code'] = 1
            response['message'] = f'Invalid request event "{event}"!'
            response['num-of-peers'] = None
            response['peers'] = None

            self.log(f'Peer {request["peer_id"]} requested with invalid request event "{event}"!')

        connectionSocket.send(obj_encode(response))


if __name__ == '__main__':
    import configargparse

    parser = configargparse.ArgParser()
    parser.add_argument('-N', '--name', type=str, default='tracker', help='Name of the tracker')
    parser.add_argument('-D', '--dir', type=str, default='sandbox/tracker/', help='Base directory of the tracker')
    parser.add_argument('-H', '--host', type=str, default='', help='Host of the tracker')
    parser.add_argument('-P', '--port', type=int, default=7889, help='Port of the tracker')
    tracker = Tracker('tracker')
    tracker.start()