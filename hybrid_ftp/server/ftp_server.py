import socket
import threading
from .client_handler import ClientHandler
from ..common.constants import TCP_PORT


class FTPServer:
    def __init__(self, host="0.0.0.0", port=TCP_PORT):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.running = True
        print(f"[FTP Server] Listening on {self.host}:{self.port}")
        try:
            while self.running:
                conn, addr = self.sock.accept()
                print(f"[FTP Server] New connection from {addr}")
                handler = ClientHandler(conn, addr)
                handler.start()
        except KeyboardInterrupt:
            print("\n[FTP Server] Shutting down...")
        finally:
            self.sock.close()

    def stop(self):
        self.running = False


