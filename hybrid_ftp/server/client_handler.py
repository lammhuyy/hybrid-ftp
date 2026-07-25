import os
import time
import threading
from ..common.control_protocol import read_line, send_line, send_reply, parse_command, parse_port, format_port
from ..common.constants import REPLIES
from ..common.checksum import sha256_file
from ..common.rdt_socket import ReliableUDPSocket
from .auth import authenticate, user_exists
from . import vfs
from . import data_channel_srv as dcs


class ClientHandler(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.session = _SessionWrap(conn, addr)
        self.running = True

    def run(self):
        self.session.update_time()
        send_reply(self.session.conn, 220)
        while self.running:
            try:
                line = read_line(self.session.conn)
            except (ConnectionError, OSError):
                break
            if not line:
                break
            self.session.update_time()
            cmd, arg = parse_command(line)
            self._dispatch(cmd, arg)
        self._cleanup()

    def _dispatch(self, cmd, arg):
        handler = getattr(self, f"cmd_{cmd}", None)
        if handler is None:
            send_reply(self.session.conn, 502)
            return
        if cmd not in ("USER", "PASS", "QUIT", "NOOP", "HELP") and not self.session.authenticated:
            send_reply(self.session.conn, 530)
            return
        handler(arg)

    def cmd_USER(self, arg):
        if not arg:
            send_reply(self.session.conn, 501)
            return
        if not user_exists(arg):
            send_reply(self.session.conn, 530)
            return
        self.session.pending_user = arg
        send_reply(self.session.conn, 331)

    def cmd_PASS(self, arg):
        if not self.session.pending_user:
            send_reply(self.session.conn, 503)
            return
        ok, root = authenticate(self.session.pending_user, arg)
        if ok:
            self.session.authenticated = True
            self.session.username = self.session.pending_user
            self.session.root = root
            self.session.cwd = "/"
            if not os.path.exists(root):
                os.makedirs(root, exist_ok=True)
            send_reply(self.session.conn, 230, f"User {self.session.username} logged in, proceed.")
        else:
            self.session.pending_user = ""
            send_reply(self.session.conn, 530)

    def cmd_QUIT(self, arg):
        send_reply(self.session.conn, 221)
        self.running = False

    def cmd_NOOP(self, arg):
        send_reply(self.session.conn, 200)

    def cmd_PORT(self, arg):
        try:
            ip, port = parse_port(arg)
        except (ValueError, IndexError):
            send_reply(self.session.conn, 501)
            return
        dcs.open_active(self.session, ip, port)
        send_reply(self.session.conn, 200)

    def cmd_PASV(self, arg):
        addr = dcs.open_passive(self.session)
        h1, h2, h3, h4 = addr[0].split(".")
        p1, p2 = addr[1] >> 8, addr[1] & 0xFF
        reply = REPLIES[227].format(h1=h1, h2=h2, h3=h3, h4=h4, p1=p1, p2=p2)
        self.session.conn.sendall(reply.encode())

    def cmd_RETR(self, arg):
        if not arg:
            send_reply(self.session.conn, 501)
            return
        if self.session.data_mode == "NONE":
            send_reply(self.session.conn, 425)
            return
        try:
            abs_path = self.session.abs_path(arg)
            if not vfs.is_file(abs_path):
                send_reply(self.session.conn, 550, "File not found.")
                return
            sz = vfs.file_size(abs_path)
            send_reply(self.session.conn, 150, f"Opening BINARY mode data connection for {arg} ({sz} bytes).")
            self._do_retr(abs_path)
            send_reply(self.session.conn, 226)
        except (PermissionError, OSError) as e:
            send_reply(self.session.conn, 550, str(e))

    def cmd_STOR(self, arg):
        if not arg:
            send_reply(self.session.conn, 501)
            return
        if self.session.data_mode == "NONE":
            send_reply(self.session.conn, 425)
            return
        try:
            abs_path = self.session.abs_path(arg)
            send_reply(self.session.conn, 150,
                       f"Opening BINARY mode data connection for {arg}.")
            self._do_stor(abs_path)
            send_reply(self.session.conn, 226)
        except (PermissionError, OSError) as e:
            send_reply(self.session.conn, 550, str(e))

    def cmd_STOU(self, arg):
        if self.session.data_mode == "NONE":
            send_reply(self.session.conn, 425)
            return
        try:
            abs_dir = self.session.abs_path("")
            full_path, name = vfs.generate_unique_path(abs_dir)
            send_reply(self.session.conn, 150,
                       f"Opening BINARY mode data connection for {name}.")
            self._do_stor(full_path)
            send_reply(self.session.conn, 226)
        except OSError as e:
            send_reply(self.session.conn, 550, str(e))

    def cmd_APPE(self, arg):
        if not arg:
            send_reply(self.session.conn, 501)
            return
        if self.session.data_mode == "NONE":
            send_reply(self.session.conn, 425)
            return
        try:
            abs_path = self.session.abs_path(arg)
            send_reply(self.session.conn, 150,
                       f"Opening BINARY mode data connection for {arg}.")
            self._do_appe(abs_path)
            send_reply(self.session.conn, 226)
        except (PermissionError, OSError) as e:
            send_reply(self.session.conn, 550, str(e))

    def cmd_HASH(self, arg):
        if not arg:
            send_reply(self.session.conn, 501)
            return
        try:
            abs_path = self.session.abs_path(arg)
            if vfs.is_file(abs_path):
                digest = sha256_file(abs_path)
                send_reply(self.session.conn, 213, digest)
            else:
                send_reply(self.session.conn, 550, "File not found.")
        except (PermissionError, OSError):
            send_reply(self.session.conn, 550, "Cannot access file.")

    def cmd_ABOR(self, arg):
        send_reply(self.session.conn, 426)

    def cmd_HELP(self, arg):
        send_reply(self.session.conn, 214)
