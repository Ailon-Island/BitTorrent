import os
import threading
from socket import *

from ..utils import *
from .rdt_socket import rdt_socket


class Server(threading.Thread):
    def __init__(self, host="", port=7889, recv_fn=None):
        self.host = host
        self.port = port
        self.serverSocket = socket(AF_INET, SOCK_STREAM)
        self.serverSocket.bind((host, self.port))
        self.serverSocket.listen(1)
        self.recv_fn = recv_fn

    def run(self):
        while True:
            connectionSocket, addr = self.serverSocket.accept()
            rdt = rdt_socket(connectionSocket)
            package = rdt.recvBytes()
            file = obj_decode(package)
            if self.recv_fn:
                self.recv_fn(file, connectionSocket)

    def __del__(self):
        self.serverSocket.close()