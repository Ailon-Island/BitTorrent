import os
import time
import threading
from socket import *

from .utils import *
from .rdt_socket import rdt_socket


class Client(threading.Thread):
    def __init__(self, host="", port=7889, recv_fn=None):
        """
        A client that connects to a server, sends files to the server, receives files from the server, and calls recv_fn when a file is received
        :param host:
        :param port:
        """
        super().__init__()

        self.host = host
        self.port = port
        self.files = []
        self.running = False

    def send_file(self, file, recv_fn=None):
        self.files.append((file, recv_fn))

    @property
    def busy(self):
        return len(self.files) > 0

    def stop(self):
        if self.running:
            self.running = False

    def run(self):
        self.running = True
        connectionSocket = None

        while self.running:
            if len(self.files) > 0:
                connectionSocket = socket.socket(AF_INET, SOCK_STREAM)
                connectionSocket.connect((self.host, self.port))
                rdt = rdt_socket(connectionSocket)
                file, recv_fn = self.files.pop(0)
                # print(f"Sending file to {self.host}:{self.port}")
                package = obj_encode(file)
                rdt.sendBytes(package)
                package_back = rdt.recvBytes()
                file_back = obj_decode(package_back)
                # print(f"Received file from {self.host}:{self.port}")
                if recv_fn:
                    recv_fn(file_back, connectionSocket)
            else:
                time.sleep(0.1)
        
        if connectionSocket:
            connectionSocket.close()


class PeerClient(threading.Thread):
    def __init__(self, peer_id=None, host="", port=7889, recv_fn=None, states=None):
        super().__init__()

        self.host = host
        self.port = port
        self.connectionSocket = socket.socket(AF_INET, SOCK_STREAM)
        self.recv_fn = recv_fn
        self.peer_id = f"{host}:{port}" if peer_id is None else peer_id
        self.states = states.copy()
        self.running = False
        self.file_init = None
        self.socket_init = None

    def set_server(self, file, socket=None):
        self.file_init = file
        self.socket_init = socket

    def run(self):
        """
        Send a file and serve the server's response, round n round
        """
        self.running = True
        if self.recv_fn is None:
            raise Exception("recv_fn cannot be None for PeerClient!")

        soc, file = self.socket_init, self.file_init

        if soc is None:
            self.connectionSocket.connect((self.host, self.port))
            rdt = rdt_socket(self.connectionSocket)
        else:
            self.connectionSocket = soc
            rdt = rdt_socket(self.connectionSocket)

        while self.running:
            package = obj_encode(file)
            rdt.sendBytes(package)
            package_back = rdt.recvBytes()
            file_back = obj_decode(package_back)
            file, stop = self.recv_fn(self.peer_id, file_back, self.connectionSocket, self.states)
            if stop:
                self.stop()
                break

        self.connectionSocket.close()

    def stop(self):
        self.running = False

    def __del__(self):
        self.connectionSocket.close()


