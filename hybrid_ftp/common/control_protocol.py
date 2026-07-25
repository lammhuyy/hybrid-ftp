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


def parse_command(line):
    parts = line.strip().split(None, 1)
    cmd = parts[0].upper() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


def format_port(h1, h2, h3, h4, p1, p2):
    return f"{h1},{h2},{h3},{h4},{p1},{p2}"


def parse_port(arg):
    parts = [int(x) for x in arg.split(",")]
    if len(parts) != 6:
        raise ValueError("PORT requires 6 comma-separated values")
    ip = ".".join(str(p) for p in parts[:4])
    port = (parts[4] << 8) | parts[5]
    return ip, port


def parse_pasv_reply(line):
    import re
    m = re.search(r"\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)", line)
    if not m:
        raise ValueError(f"Cannot parse PASV reply: {line}")
    parts = [int(g) for g in m.groups()]
    ip = ".".join(str(p) for p in parts[:4])
    port = (parts[4] << 8) | parts[5]
    return ip, port
