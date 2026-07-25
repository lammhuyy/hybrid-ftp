import socket
import time
import random
from .constants import (
    MAX_PAYLOAD, MAX_WINDOW, FLAG_SYN, FLAG_ACK, FLAG_FIN, FLAG_DATA, FLAG_LAST,
    INITIAL_RTO_MS, MIN_RTO_MS, MAX_RTO_MS, INITIAL_CWND, HANDSHAKE_TIMEOUT_S,
    TRANSFER_IDLE_TIMEOUT_S,
)
from .rdt_header import build_packet, parse_packet, has_flag


class ReliableUDPSocket:
    def __init__(self, sock=None):
        self.sock = sock if sock else socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.remote_addr = None
        self.local_seq_init = random.randint(0, 2 ** 31 - 1)
        self.peer_seq_init = 0
        self.handshake_done = False

    def bind(self, addr):
        self.sock.bind(addr)

    def connect(self, addr):
        self.remote_addr = addr
        return self._handshake_initiate()

    def accept(self):
        return self._handshake_wait()

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

    def _handshake_initiate(self):
        my_seq = self.local_seq_init
        pkt = build_packet(seq_num=my_seq, flags=FLAG_SYN, window=MAX_WINDOW)
        self.sock.sendto(pkt, self.remote_addr)
        self.sock.settimeout(5.0)
        deadline = time.time() + HANDSHAKE_TIMEOUT_S
        while time.time() < deadline:
            try:
                data, _ = self.sock.recvfrom(4096)
                hdr = parse_packet(data)
                if has_flag(hdr["flags"], FLAG_SYN) and has_flag(hdr["flags"], FLAG_ACK):
                    if hdr["ack_num"] == my_seq + 1:
                        self.peer_seq_init = hdr["seq_num"]
                        ack = build_packet(ack_num=hdr["seq_num"] + 1, flags=FLAG_ACK, window=MAX_WINDOW)
                        self.sock.sendto(ack, self.remote_addr)
                        self.handshake_done = True
                        return
            except socket.timeout:
                if time.time() < deadline:
                    self.sock.sendto(pkt, self.remote_addr)
        raise TimeoutError("RDT handshake initiate timed out")

    def _handshake_wait(self):
        while True:
            data, addr = self.sock.recvfrom(4096)
            try:
                hdr = parse_packet(data)
            except ValueError:
                continue
            if has_flag(hdr["flags"], FLAG_SYN) and not has_flag(hdr["flags"], FLAG_ACK):
                self.remote_addr = addr
                self.peer_seq_init = hdr["seq_num"]
                my_seq = self.local_seq_init
                pkt = build_packet(seq_num=my_seq, ack_num=hdr["seq_num"] + 1, flags=FLAG_SYN | FLAG_ACK, window=MAX_WINDOW)
                self.sock.sendto(pkt, addr)
                self.sock.settimeout(5.0)
                deadline = time.time() + HANDSHAKE_TIMEOUT_S
                while time.time() < deadline:
                    try:
                        data, _ = self.sock.recvfrom(4096)
                        hdr2 = parse_packet(data)
                        if has_flag(hdr2["flags"], FLAG_ACK) and hdr2["ack_num"] == my_seq + 1:
                            self.handshake_done = True
                            return addr
                    except socket.timeout:
                        if time.time() < deadline:
                            self.sock.sendto(pkt, addr)
                raise TimeoutError("RDT handshake wait timed out")

    def send(self, data_iterable):
        sender = _Sender(self.sock, self.remote_addr)
        return sender.send_all(data_iterable)

    def recv(self):
        receiver = _Receiver(self.sock, self.remote_addr)
        return receiver.recv_all()


class _Sender():
    pass


class _Receiver():
    pass