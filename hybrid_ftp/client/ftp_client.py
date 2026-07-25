import socket
import os
import sys
from ..common.control_protocol import read_line, send_line, parse_command, format_port, parse_port, parse_pasv_reply
from ..common.checksum import sha256_file, sha256_data
from ..common.rdt_socket import ReliableUDPSocket
from .data_channel_cli import open_passive_sender, open_port_listener
from .transfer import Progress, read_file_chunks


class FTPClient:
    def __init__(self):
        self.control = None
        self.connected = False
        self.authenticated = False
        self.cwd = "/"
        self.data_mode = "NONE"
        self.pasv_addr = None
        self.port_addr = None
        self.data_socket = None
        self.type = "A"

    def connect(self, host="127.0.0.1", port=2121):
        self.control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control.connect((host, port))
        self.connected = True
        resp = self._read_reply()
        print(resp)
