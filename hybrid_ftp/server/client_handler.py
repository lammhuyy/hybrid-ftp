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

