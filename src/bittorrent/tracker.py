import os
import time
import datetime
import threading
from socket import *

from components import *
from utils import *


class Tracker(threading.Thread):
    def __init__(self, name, base_dir="sandbox/tracker/", host="", port=7889):
        super().__init__()

        self.cmd_lock = threading.Lock()
        self.cmd_queue = []
        self.name = name
        self.dir = base_dir
        self.log_lock = threading.Lock()
        self.log = self.init_log(name, base_dir, self.log_lock)
        self.host = host
        self.port = port
        self.peers = {}
        self.server = Server(host, port, self.respond)
        self.running = False
        self.log(f'[INIT] Tracker {self.name} is initialized')

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
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        log_file = os.path.join(log_dir, f'{name}_{timestamp}.log')

        def log(msg):
            with lock:
                log_fn(msg, log_file)

        return log
    
    def stop(self):
        if self.running:
            self.running = False

    def run(self):
        self.running = True

        self.server.start()

        self.log(f'[START] Tracker {self.name} is running on {self.host}:{self.port}')

        while self.running:
            try:
                cmd_line = self.get_cmd()
                if cmd_line:
                    cmd, *args = cmd_line.split()
                    if cmd in ['quit', 'q']:
                        self.stop()
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.log("[ERROR] Tracker get exception:", type(e).__name__)

        self.log('[STOP] Stopping server...')
        self.server.stop()
        self.server.join()
        self.log('[STOP] Server stopped')
        self.log(f'[STOP] Tracker {self.name} stopped')
    
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
        
        return response


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Tracker')
    parser.add_argument('-N', '--name', type=str, default='tracker', help='Name of the tracker')
    parser.add_argument('-D', '--dir', type=str, default='sandbox/tracker/', help='Base directory of the tracker')
    parser.add_argument('-H', '--host', type=str, default='', help='Host of the tracker')
    parser.add_argument('-P', '--port', type=int, default=7889, help='Port of the tracker')
    args = parser.parse_args()

    tracker = Tracker(args.name, args.dir, args.host, args.port)
    tracker.start()
    time.sleep(0.1)

    try:
        while True:
            if tracker.running:
                cmd = input('Please enter command: ')
                tracker.cmd(cmd)
                if cmd in ['quit', 'q']:
                    tracker.join()
                    break
            # print(f'[INFO] Tracker stopped: {tracker.stop_flag.is_set()}')
    except KeyboardInterrupt:
        print('\n[STOP] Keyboard Interrupt, stopping tracker...')
        tracker.stop()
        tracker.join()
            
    print('[INFO] Program exited')