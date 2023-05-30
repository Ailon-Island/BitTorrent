import socket
import struct


FILE_HEADER_SIZE = 8
class rdt_socket(object):
    def __init__(self, s : socket):
        self.s = s
        self.databuf = bytes()

    def sendBytes(self, f : bytearray):
        try:
            l = len(f)
            header = struct.pack('!1Q', l)
            send_data = header + f
            self.s.sendall(send_data)
        except socket.error as e:
            print(e)
            print(e.filename)
            
    def recvBytes(self):
        if len(self.databuf) >= FILE_HEADER_SIZE:
            header = struct.unpack("!1Q", self.databuf[:FILE_HEADER_SIZE])
            body_size = header[0]
            if len(self.databuf) >= FILE_HEADER_SIZE + body_size:
                body = self.databuf[FILE_HEADER_SIZE:FILE_HEADER_SIZE + body_size]
                self.databuf = self.databuf[FILE_HEADER_SIZE+body_size:]
                return body
        while True:
            data = self.s.recv(1024)
            if data:
                self.databuf += data
                while True:
                    if len(self.databuf) < FILE_HEADER_SIZE:
                        break
                    header = struct.unpack("!1Q", self.databuf[:FILE_HEADER_SIZE])
                    body_size = header[0]
                    if len(self.databuf) < FILE_HEADER_SIZE + body_size:
                        break
                    body = self.databuf[FILE_HEADER_SIZE:FILE_HEADER_SIZE + body_size]
                    self.databuf = self.databuf[FILE_HEADER_SIZE+body_size:]
                    return body