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


class _Sender:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.base = 1
        self.next_seq = 1
        self.cwnd = INITIAL_CWND
        self.ssthresh = MAX_WINDOW * 2
        self.peer_window = MAX_WINDOW
        self.buffer = {}
        self.estimated_rtt = INITIAL_RTO_MS / 1000.0
        self.dev_rtt = 0.0
        self.closed = False

    @property
    def window(self):
        return max(1, min(int(self.cwnd), self.peer_window))

    def _update_rto(self, sample_rtt):
        self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
        self.dev_rtt = 0.75 * self.dev_rtt + 0.25 * abs(sample_rtt - self.estimated_rtt)
        rto = self.estimated_rtt + 4 * self.dev_rtt
        return max(MIN_RTO_MS / 1000.0, min(rto, MAX_RTO_MS / 1000.0))

    def send_all(self, data_iterable):
        self.sock.settimeout(0.1)
        iterator = iter(data_iterable)
        eof = False
        idle_deadline = time.time() + TRANSFER_IDLE_TIMEOUT_S

        while True:
            if time.time() > idle_deadline and self.buffer:
                raise TimeoutError("Send timed out: no ACK progress")

            while self.next_seq < self.base + self.window and not eof:
                try:
                    chunk = next(iterator)
                except StopIteration:
                    eof = True
                    break
                self._send_packet(self.next_seq, chunk)
                self.next_seq += 1

            before = len(self.buffer)
            self._recv_acks()
            if len(self.buffer) < before:
                idle_deadline = time.time() + TRANSFER_IDLE_TIMEOUT_S

            self._check_timers()

            if eof and self.base >= self.next_seq:
                return self._finish()

    def _send_packet(self, seq, chunk):
        chunk = bytes(chunk)
        pkt = build_packet(seq_num=seq, flags=FLAG_DATA, window=MAX_WINDOW, payload=chunk)
        self.sock.sendto(pkt, self.addr)
        self.buffer[seq] = [chunk, time.time(), INITIAL_RTO_MS / 1000.0, 0]

    def _recv_acks(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(4096)
            except socket.timeout:
                return
            try:
                hdr = parse_packet(data)
            except ValueError:
                continue
            if has_flag(hdr["flags"], FLAG_ACK):
                self._process_ack(hdr)

    def _process_ack(self, hdr):
        ack_num = hdr["ack_num"]
        if ack_num not in self.buffer:
            return
        sample_rtt = time.time() - self.buffer[ack_num][1]
        self._update_rto(sample_rtt)
        del self.buffer[ack_num]
        while self.base not in self.buffer and self.base < self.next_seq:
            self.base += 1
        self.peer_window = hdr["window"]
        if self.cwnd < self.ssthresh:
            self.cwnd += 1
        else:
            self.cwnd += 1.0 / self.cwnd
        self.cwnd = min(self.cwnd, MAX_WINDOW)

    def _check_timers(self):
        now = time.time()
        to_retransmit = []
        for seq, info in list(self.buffer.items()):
            _, send_time, rto, retries = info
            if now - send_time >= rto:
                to_retransmit.append((seq, rto, retries))
        for seq, old_rto, retries in to_retransmit:
            chunk, _, _, _ = self.buffer[seq]
            pkt = build_packet(seq_num=seq, flags=FLAG_DATA, window=MAX_WINDOW, payload=chunk)
            self.sock.sendto(pkt, self.addr)
            new_rto = min(old_rto * 2, MAX_RTO_MS / 1000.0)
            self.buffer[seq] = [chunk, time.time(), new_rto, retries + 1]
            self.ssthresh = max(int(self.cwnd) // 2, 2)
            self.cwnd = INITIAL_CWND

    def _finish(self):
        fin = build_packet(seq_num=0, flags=FLAG_FIN, window=MAX_WINDOW)
        self.sock.sendto(fin, self.addr)
        self.sock.settimeout(2.0)
        deadline = time.time() + HANDSHAKE_TIMEOUT_S
        while time.time() < deadline:
            try:
                data, _ = self.sock.recvfrom(4096)
                hdr = parse_packet(data)
                if has_flag(hdr["flags"], FLAG_FIN) and has_flag(hdr["flags"], FLAG_ACK):
                    self.closed = True
                    return True
            except (socket.timeout, ValueError):
                if time.time() < deadline:
                    self.sock.sendto(fin, self.addr)
                    self.sock.settimeout(2.0)
        self.closed = True
        return True



class _Receiver():
    pass