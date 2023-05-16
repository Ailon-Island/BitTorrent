from socket import *
import argparse
import os

from src.utils import *


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Server')
    parser.add_argument('-p', '--port', type=int, default=7889, help='Port number')
    opt = parser.parse_args()

    # create a socket
    serverSocket = socket(AF_INET, SOCK_STREAM)
    # prepare a server socket
    serverSocket.bind(('', opt.port))
    serverSocket.listen(1)

    while True:
        # establish the connection
        print('Ready to serve...')
        connectionSocket, addr = serverSocket.accept()
        try:
            # receive the file name
            file = connectionSocket.recv(1024).decode()
            # open the file
            with open(os.path.join("server", file), 'wb') as f:
                # receive the file content
                while True:
                    content = connectionSocket.recv(1024)
                    if not content:
                        break
                    f.write(content)
            # send a success message
            print(f'File "{file}" received successfully.')
        except IOError:
            # send a failure message
            print('File cannot be received.')
        # close the socket
        connectionSocket.close()
    
    serverSocket.close()
