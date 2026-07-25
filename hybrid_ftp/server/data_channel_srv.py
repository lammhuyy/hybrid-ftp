import socket
from ..common.rdt_socket import ReliableUDPSocket


def open_passive(session):
    rdt_sock = ReliableUDPSocket()
    rdt_sock.bind(("0.0.0.0", 0))
    session.data_socket = rdt_sock
    session.data_mode = "PASSIVE"
    addr = rdt_sock.sock.getsockname()
    ip = session.server_ip_for_client
    if ip == "0.0.0.0" or ip.startswith("127."):
        ip = "127.0.0.1"
    return (ip, addr[1])


def open_active(session, ip, port):
    rdt_sock = ReliableUDPSocket()
    rdt_sock.bind(("0.0.0.0", 0))
    peer = (ip, port)
    session.data_socket = rdt_sock
    session.data_mode = "ACTIVE"
    session.peer_addr = peer
    return rdt_sock

def open_active(session, ip, port):
    rdt_sock = ReliableUDPSocket()
    rdt_sock.bind(("0.0.0.0", 0))
    peer = (ip, port)
    session.data_socket = rdt_sock
    session.data_mode = "ACTIVE"
    session.peer_addr = peer
    return rdt_sock
