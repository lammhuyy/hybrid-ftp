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

    def login(self, user, password):
        send_line(self.control, f"USER {user}")
        resp = self._read_reply()
        print(resp)
        if not resp.startswith("331"):
            return False
        send_line(self.control, f"PASS {password}")
        resp = self._read_reply()
        print(resp)
        if resp.startswith("230"):
            self.authenticated = True
            return True
        return False

    def pasv(self):
        send_line(self.control, "PASV")
        resp = self._read_reply()
        print(resp)
        if resp.startswith("227"):
            ip, port = parse_pasv_reply(resp)
            self.data_mode = "PASSIVE"
            self.pasv_addr = (ip, port)
            return True
        return False

    def port(self):
        rdt, addr = open_port_listener()
        self.data_socket = rdt
        self.data_mode = "ACTIVE"
        local_ip = self.control.getsockname()[0]
        if local_ip == "0.0.0.0":
            local_ip = "127.0.0.1"
        self.port_addr = (local_ip, addr[1])
        h1, h2, h3, h4 = local_ip.split(".")
        p1, p2 = addr[1] >> 8, addr[1] & 0xFF
        send_line(self.control, f"PORT {format_port(h1, h2, h3, h4, p1, p2)}")
        resp = self._read_reply()
        print(resp)
        return resp.startswith("200")

    def pasv(self):
        send_line(self.control, "PASV")
        resp = self._read_reply()
        print(resp)
        if resp.startswith("227"):
            ip, port = parse_pasv_reply(resp)
            self.data_mode = "PASSIVE"
            self.pasv_addr = (ip, port)
            return True
        return False

    def port(self):
        rdt, addr = open_port_listener()
        self.data_socket = rdt
        self.data_mode = "ACTIVE"
        local_ip = self.control.getsockname()[0]
        if local_ip == "0.0.0.0":
            local_ip = "127.0.0.1"
        self.port_addr = (local_ip, addr[1])
        h1, h2, h3, h4 = local_ip.split(".")
        p1, p2 = addr[1] >> 8, addr[1] & 0xFF
        send_line(self.control, f"PORT {format_port(h1, h2, h3, h4, p1, p2)}")
        resp = self._read_reply()
        print(resp)
        return resp.startswith("200")

    def retr(self, remote_path, local_path=None):
        if local_path is None:
            local_path = os.path.basename(remote_path)
        send_line(self.control, f"RETR {remote_path}")
        resp = self._read_reply()
        print(resp)
        if not resp.startswith("150"):
            return False
        rdt = self._setup_data_channel(is_sender=False)
        if rdt is None:
            return False
        try:
            data = rdt.recv()
            with open(local_path, "wb") as f:
                f.write(data)
            resp2 = self._read_reply()
            print(resp2)
            print(f"  Downloaded {len(data)} bytes to {local_path}")
            return True
        finally:
            try:
                rdt.close()
            except Exception:
                pass
            self._reset_data()

    def stor(self, local_path, remote_path=None):
        if remote_path is None:
            remote_path = os.path.basename(local_path)
        if not os.path.exists(local_path):
            print(f"  Local file not found: {local_path}")
            return False
        send_line(self.control, f"STOR {remote_path}")
        resp = self._read_reply()
        print(resp)
        if not resp.startswith("150"):
            return False
        rdt = self._setup_data_channel(is_sender=True)
        if rdt is None:
            return False
        try:
            rdt.send(read_file_chunks(local_path))
            resp2 = self._read_reply()
            print(resp2)
            print(f"  Uploaded {local_path} to {remote_path}")
            return True
        finally:
            try:
                rdt.close()
            except Exception:
                pass
            self._reset_data()

    def list(self, path=""):
        if path:
            send_line(self.control, f"LIST {path}")
        else:
            send_line(self.control, "LIST")
        resp = self._read_reply()
        print(resp)
        if not resp.startswith("150"):
            return
        rdt = self._setup_data_channel(is_sender=False)
        if rdt is None:
            return
        try:
            data = rdt.recv()
            print(data.decode("utf-8", errors="replace"))
            resp2 = self._read_reply()
            print(resp2)
        finally:
            try:
                rdt.close()
            except Exception:
                pass
            self._reset_data()

    def hash(self, path):
        send_line(self.control, f"HASH {path}")
        resp = self._read_reply()
        print(resp)
        if resp.startswith("213"):
            return resp[4:].strip()
        return None
