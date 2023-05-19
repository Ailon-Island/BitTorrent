import os
import threading
from socket import *

from ..utils import *
from .rdt_socket import rdt_socket


class Client(threading.Thread):
    def __init__(self, host="", port=7889):
        self.host = host
        self.port = port
        self.connectionSocket = socket(AF_INET, SOCK_STREAM)
        self.connectionSocket.connect((host, port))
        self.rdt = rdt_socket(self.connectionSocket)

    def send(self, file, recv_fn=None):
        package = obj_encode(file)
        self.rdt.sendBytes(package)
        package_back = self.rdt.recvBytes()
        file_back = obj_decode(package_back)
        if recv_fn:
            recv_fn(file_back)

    def __del__(self):
        self.connectionSocket.close()
