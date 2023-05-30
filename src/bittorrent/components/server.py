import os
import threading
from socket import *

from .utils import *
from .rdt_socket import rdt_socket


class Server(threading.Thread):
    def __init__(self, host="", port=7889, recv_fn=None):
        """
        A server that listens to a port, receives files from clients, and calls recv_fn when a file is received
        :param host:
        :param port:
        :param recv_fn:
        """
        super().__init__()

        self.host = host
        self.port = port
        self.serverSocket = socket.socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind((host, self.port))
        self.serverSocket.listen(1)
        self.serverSocket.setblocking(False)
        self.recv_fn = recv_fn
        self.running = False
        # self.stop_flag = threading.Event()

    def run(self):
        self.running = True
        # while not self.stop_flag.is_set():
        while self.running:
            try:
                connectionSocket, addr = self.serverSocket.accept()
                rdt = rdt_socket(connectionSocket)
                package = rdt.recvBytes()
                file = obj_decode(package)
                if self.recv_fn:
                    response = self.recv_fn(file, connectionSocket)
                    package_back = obj_encode(response)
                    rdt.sendBytes(package_back)
            except BlockingIOError:
                pass
            except Exception as e:
                print("Server get exception:", type(e).__name__)
        
        self.serverSocket.close()
                
    def stop(self):
        if self.running:
            self.running = False
