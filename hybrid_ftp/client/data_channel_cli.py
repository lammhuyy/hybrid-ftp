import socket
from ..common.rdt_socket import ReliableUDPSocket


def open_passive_sender(ip, port):
    rdt = ReliableUDPSocket()
    rdt.sock.bind(("0.0.0.0", 0))
    if ip == "0.0.0.0":
        ip = "127.0.0.1"
    rdt.connect((ip, port))
    return rdt


def open_port_listener(bind_ip="0.0.0.0"):
    rdt = ReliableUDPSocket()
    rdt.sock.bind((bind_ip, 0))
    addr = rdt.sock.getsockname()
    return rdt, addr

def open_port_listener(bind_ip="0.0.0.0"):
    rdt = ReliableUDPSocket()
    rdt.sock.bind((bind_ip, 0))
    addr = rdt.sock.getsockname()
    return rdt, addr
