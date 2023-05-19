import os
import threading
from socket import *

from ..utils import *
from .rdt_socket import rdt_socket


class Client(threading.Thread):
    def __init__(self, host="", port=7889, recv_fn=None):
        """
        A client that connects to a server, sends files to the server, receives files from the server, and calls recv_fn when a file is received
        :param host:
        :param port:
        """
        self.host = host
        self.port = port
        self.connectionSocket = socket(AF_INET, SOCK_STREAM)
        self.recv_fn = recv_fn

    def send(self, file):
        self.connectionSocket.connect((self.host, self.port))
        rdt = rdt_socket(self.connectionSocket)
        package = obj_encode(file)
        rdt.sendBytes(package)
        package_back = rdt.recvBytes()
        file_back = obj_decode(package_back)
        if self.recv_fn:
            self.recv_fn(file_back, self.connectionSocket)
        self.connectionSocket.close()

    def send_and_serve(self, file):
        """
        Send a file and serve the server's response
        :param file:
        :return:
        """
        if self.recv_fn is None:
            raise Exception("recv_fn cannot be None for send_and_serve!")

        self.connectionSocket.connect((self.host, self.port))
        rdt = rdt_socket(self.connectionSocket)
        while True:
            package = obj_encode(file)
            rdt.sendBytes(package)
            package_back = rdt.recvBytes()
            file_back = obj_decode(package_back)
            file = self.recv_fn(file_back, self.connectionSocket)

    def __del__(self):
        self.connectionSocket.close()



