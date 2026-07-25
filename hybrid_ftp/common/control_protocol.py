import socket


CRLF = b"\r\n"


def read_line(sock):
    buf = b""
    while True:
        ch = sock.recv(1)
        if not ch:
            raise ConnectionError("Connection closed")
        buf += ch
        if buf.endswith(CRLF):
            return buf[:-2].decode("utf-8", errors="replace")


def send_line(sock, line):
    data = (line + "\r\n").encode("utf-8")
    sock.sendall(data)


def send_reply(sock, code, text=""):
    line = f"{code} {text}" if text else f"{code}"
    send_line(sock, line)

