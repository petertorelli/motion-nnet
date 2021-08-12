#!/usr/bin/env python3
import socket
import sys
def send_movie(filename, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((socket.gethostname(), port))
    sock.send(filename.encode('utf-8'))
    sock.close()
if __name__ == "__main__":
    send_movie(sys.argv[1], 19011)
