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

    def nlst(self, path=""):
        if path:
            send_line(self.control, f"NLST {path}")
        else:
            send_line(self.control, "NLST")
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

    def _setup_data_channel(self, is_sender):
        if self.data_mode == "PASSIVE":
            rdt = open_passive_sender(self.pasv_addr[0], self.pasv_addr[1])
            return rdt
        elif self.data_mode == "ACTIVE":
            rdt = self.data_socket
            rdt.accept()
            return rdt
        else:
            print("  No data channel established. Use PASV or PORT first.")
            return None

    def _reset_data(self):
        self.data_mode = "NONE"
        self.data_socket = None

    def _read_reply(self):
        return read_line(self.control)

    def close(self):
        if self.connected:
            try:
                send_line(self.control, "QUIT")
                self._read_reply()
            except Exception:
                pass
            self.control.close()
            self.connected = False

    def send_raw(self, cmd):
        send_line(self.control, cmd)
        return self._read_reply()


def main():
    import sys
    client = FTPClient()
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = "127.0.0.1"
    try:
        client.connect(host)
        while True:
            try:
                line = input("ftp> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            cmd, arg = parse_command(line)
            if cmd == "QUIT" or cmd == "EXIT":
                client.close()
                break
            elif cmd == "USER":
                if not arg:
                    print("  Usage: USER <username>")
                    continue
                pw = input("Password: ")
                client.login(arg, pw)
            elif cmd == "PASV":
                client.pasv()
            elif cmd == "PORT":
                client.port()
            elif cmd == "RETR":
                parts = arg.split(None, 1)
                remote = parts[0]
                local = parts[1] if len(parts) > 1 else None
                client.retr(remote, local)
            elif cmd == "STOR":
                parts = arg.split(None, 1)
                local = parts[0]
                remote = parts[1] if len(parts) > 1 else None
                client.stor(local, remote)
            elif cmd == "LIST":
                client.list(arg)
            elif cmd == "NLST":
                client.nlst(arg)
            elif cmd == "HASH":
                if arg:
                    d = client.hash(arg)
                else:
                    print("  Usage: HASH <filename>")
            elif cmd == "PWD":
                resp = client.send_raw("PWD")
                print(resp)
            elif cmd == "CWD":
                resp = client.send_raw(f"CWD {arg}" if arg else "CWD")
                print(resp)
            elif cmd == "CDUP":
                resp = client.send_raw("CDUP")
                print(resp)
            elif cmd == "MKD":
                resp = client.send_raw(f"MKD {arg}")
                print(resp)
            elif cmd == "RMD":
                resp = client.send_raw(f"RMD {arg}")
                print(resp)
            elif cmd == "DELE":
                resp = client.send_raw(f"DELE {arg}")
                print(resp)
            elif cmd == "RNFR":
                self.rename_from = arg
                resp = client.send_raw(f"RNFR {arg}")
                print(resp)
            elif cmd == "RNTO":
                if hasattr(client, 'rename_from') and client.rename_from:
                    resp = client.send_raw(f"RNTO {arg}")
                    print(resp)
                    client.rename_from = None
                else:
                    resp = client.send_raw(f"RNTO {arg}")
                    print(resp)
            elif cmd == "TYPE":
                resp = client.send_raw(f"TYPE {arg.upper()}")
                print(resp)
            elif cmd == "SIZE":
                resp = client.send_raw(f"SIZE {arg}")
                print(resp)
            elif cmd == "MDTM":
                resp = client.send_raw(f"MDTM {arg}")
                print(resp)
            elif cmd == "NOOP":
                resp = client.send_raw("NOOP")
                print(resp)
            elif cmd == "HELP":
                resp = client.send_raw("HELP")
                print(resp)
            elif cmd == "ABOR":
                resp = client.send_raw("ABOR")
                print(resp)
            elif cmd == "MODE":
                resp = client.send_raw(f"MODE {arg.upper()}")
                print(resp)
            elif cmd == "STOU":
                rdt = client._setup_data_channel(True)
                if rdt is None:
                    continue
                if arg:
                    local = arg
                else:
                    print("  Usage: STOU <local_file>")
                    continue
                if not os.path.exists(local):
                    print(f"  Local file not found: {local}")
                    continue
                resp = client.send_raw("STOU")
                print(resp)
                if resp.startswith("150"):
                    try:
                        rdt.send(read_file_chunks(local))
                        resp2 = client._read_reply()
                        print(resp2)
                    finally:
                        try:
                            rdt.close()
                        except Exception:
                            pass
                        client._reset_data()
            elif cmd == "APPE":
                if not arg:
                    print("  Usage: APPE <remote_file> [local_file]")
                    continue
                parts = arg.split(None, 1)
                remote = parts[0]
                local = parts[1] if len(parts) > 1 else None
                if local and os.path.exists(local):
                    pass
                else:
                    print(f"  Local file not found: {local or remote}")
                    continue
                rdt = client._setup_data_channel(True)
                if rdt is None:
                    continue
                resp = client.send_raw(f"APPE {remote}")
                print(resp)
                if resp.startswith("150"):
                    try:
                        rdt.send(read_file_chunks(local))
                        resp2 = client._read_reply()
                        print(resp2)
                    finally:
                        try:
                            rdt.close()
                        except Exception:
                            pass
                        client._reset_data()
            else:
                resp = client.send_raw(line)
                print(resp)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
