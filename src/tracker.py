import os
import datetime
import threading
from socket import *

from components import *
from utils import *


class Tracker:
    def __init__(self, name, folder="", host="", port=7889):
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
        self.peers = {}
        self.server = Server(host, port, self.respond)

        self.log(f'[INIT] Tracker {self.name} is initialized')

    def start(self):
        self.server.start()

        self.log(f'[START] Tracker {self.name} is running on {self.host}:{self.port}')
    
    def respond(self, request, connectionSocket):
        self.log(f'[REQUEST] Received request: {request}')

        response = {
            'error_code': 0,
            'message': None,
            'num-of-peers': len(self.peers),
            'peers': self.peers.copy()
        }

        t = request['type']
        if t == 'started':
            if request['peer_id'] not in self.peers:
                self.peers[request['peer_id']] = {}
            self.peers[request['peer_id']]['ip'] = request['ip']
            self.peers[request['peer_id']]['port'] = request['port']
            self.peers[request['peer_id']]['peer_id'] = request['peer_id']

            response['message'] = 'You\'ve joined! Welcome to the P2P network!'

            self.log(f'Peer {request["peer_id"]} joined the network!')

        elif t == 'completed':
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
            response['message'] = 'Invalid request type!'
            response['num-of-peers'] = None
            response['peers'] = None

            self.log(f'Peer {request["peer_id"]} requested with invalid request type!')

        connectionSocket.send(obj_encode(response))


