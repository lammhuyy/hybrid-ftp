import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from hybrid_ftp.client.ftp_client import FTPClient


def print_usage():
    print("Usage: python run_client.py [host]")
    print("  Connects to Hybrid FTP server. Default host: 127.0.0.1")
    print()
    print("Available commands at ftp> prompt:")
    print("  USER <name> / PASS <pw>  - Login")
    print("  PASV / PORT              - Set data channel mode")
    print("  RETR <remote> [local]    - Download file")
    print("  STOR <local> [remote]    - Upload file")
    print("  LIST [path]              - List directory")
    print("  PWD / CWD / CDUP         - Directory navigation")
    print("  MKD / RMD / DELE         - File operations")
    print("  HASH <file>              - Get file hash")
    print("  QUIT                     - Exit")


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    client = FTPClient()

    try:
        print(f"[FTP Client] Connecting to {host}:2121...")
        client.connect(host)
    except ConnectionRefusedError:
        print(f"  Connection refused. Is the server running on {host}:2121?")
        return
    except Exception as e:
        print(f"  Connection failed: {e}")
        return

    print_usage()

    try:
        while True:
            try:
                line = input("ftp> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue

            parts = line.split(None, 1)
            cmd = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            try:
                if cmd == "QUIT" or cmd == "EXIT":
                    client.close()
                    print("Goodbye.")
                    break
                elif cmd == "USER":
                    if not arg:
                        print("  Usage: USER <username>")
                        continue
                    import getpass
                    pw = getpass.getpass("Password: ")
                    client.login(arg, pw)
                elif cmd == "PASV":
                    client.pasv()
                elif cmd == "PORT":
                    client.port()
                elif cmd == "RETR":
                    parts = arg.split(None, 1)
                    remote = parts[0] if parts else ""
                    if not remote:
                        print("  Usage: RETR <remote_file> [local_file]")
                        continue
                    local = parts[1] if len(parts) > 1 else None
                    client.retr(remote, local)
                elif cmd == "STOR":
                    parts = arg.split(None, 1)
                    local = parts[0] if parts else ""
                    if not local:
                        print("  Usage: STOR <local_file> [remote_file]")
                        continue
                    remote = parts[1] if len(parts) > 1 else None
                    client.stor(local, remote)
                elif cmd == "STOU":
                    if not arg:
                        print("  Usage: STOU <local_file>")
                        continue
                    if not os.path.exists(arg):
                        print(f"  Local file not found: {arg}")
                        continue
                    resp = client.send_raw("STOU")
                    print(resp)
                    if resp.startswith("150"):
                        rdt = client._setup_data_channel(True)
                        if rdt is None:
                            continue
                        try:
                            rdt.send(read_file_chunks(arg))
                            resp2 = client._read_reply()
                            print(resp2)
                        finally:
                            try:
                                rdt.close()
                            except Exception:
                                pass
                            client._reset_data()
                elif cmd == "APPE":
                    parts = arg.split(None, 1)
                    remote = parts[0] if parts else ""
                    if not remote:
                        print("  Usage: APPE <remote_file> <local_file>")
                        continue
                    local = parts[1] if len(parts) > 1 else remote
                    if not os.path.exists(local):
                        print(f"  Local file not found: {local}")
                        continue
                    resp = client.send_raw(f"APPE {remote}")
                    print(resp)
                    if resp.startswith("150"):
                        rdt = client._setup_data_channel(True)
                        if rdt is None:
                            continue
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
                elif cmd == "TYPE":
                    if arg.upper() not in ("A", "I"):
                        print("  Usage: TYPE {A|I}")
                        continue
                    resp = client.send_raw(f"TYPE {arg.upper()}")
                    print(resp)
                elif cmd == "MODE":
                    if arg.upper() not in ("S", "B", "C"):
                        print("  Usage: MODE {S|B|C}")
                        continue
                    resp = client.send_raw(f"MODE {arg.upper()}")
                    print(resp)
                elif cmd == "LIST":
                    client.list(arg)
                elif cmd == "NLST":
                    client.nlst(arg)
                elif cmd == "HASH":
                    if not arg:
                        print("  Usage: HASH <filename>")
                        continue
                    d = client.hash(arg)
                elif cmd == "PWD":
                    resp = client.send_raw("PWD")
                    print(resp)
                elif cmd == "CWD":
                    if not arg:
                        print("  Usage: CWD <directory>")
                        continue
                    resp = client.send_raw(f"CWD {arg}")
                    print(resp)
                elif cmd == "CDUP":
                    resp = client.send_raw("CDUP")
                    print(resp)
                elif cmd == "MKD":
                    if not arg:
                        print("  Usage: MKD <directory>")
                        continue
                    resp = client.send_raw(f"MKD {arg}")
                    print(resp)
                elif cmd == "RMD":
                    if not arg:
                        print("  Usage: RMD <directory>")
                        continue
                    resp = client.send_raw(f"RMD {arg}")
                    print(resp)
                elif cmd == "DELE":
                    if not arg:
                        print("  Usage: DELE <file>")
                        continue
                    resp = client.send_raw(f"DELE {arg}")
                    print(resp)
                elif cmd == "RNFR":
                    if not arg:
                        print("  Usage: RNFR <source>")
                        continue
                    client.rename_from = arg
                    resp = client.send_raw(f"RNFR {arg}")
                    print(resp)
                elif cmd == "RNTO":
                    if not arg:
                        print("  Usage: RNTO <destination>")
                        continue
                    if getattr(client, 'rename_from', None):
                        resp = client.send_raw(f"RNTO {arg}")
                        print(resp)
                        client.rename_from = None
                    else:
                        print("  Use RNFR first to set source file.")
                elif cmd == "TYPE":
                    if arg.upper() not in ("A", "I"):
                        print("  Usage: TYPE {A|I}")
                        continue
                    resp = client.send_raw(f"TYPE {arg.upper()}")
                    print(resp)
                elif cmd == "MODE":
                    if arg.upper() not in ("S", "B", "C"):
                        print("  Usage: MODE {S|B|C}")
                        continue
                    resp = client.send_raw(f"MODE {arg.upper()}")
                    print(resp)
                elif cmd == "STAT":
                    if arg:
                        resp = client.send_raw(f"STAT {arg}")
                    else:
                        resp = client.send_raw("STAT")
                    print(resp)
                elif cmd == "SIZE":
                    if not arg:
                        print("  Usage: SIZE <file>")
                        continue
                    resp = client.send_raw(f"SIZE {arg}")
                    print(resp)
                elif cmd == "MDTM":
                    if not arg:
                        print("  Usage: MDTM <file>")
                        continue
                    resp = client.send_raw(f"MDTM {arg}")
                    print(resp)
                elif cmd == "NOOP":
                    resp = client.send_raw("NOOP")
                    print(resp)
                elif cmd == "ABOR":
                    resp = client.send_raw("ABOR")
                    print(resp)
                elif cmd == "HELP" or cmd == "?":
                    resp = client.send_raw("HELP")
                    print(resp)
                else:
                    print(f"  Unknown command: {cmd}")
            except TimeoutError as e:
                print(f"  [Timeout] {e}")
                client._reset_data()
            except Exception as e:
                print(f"  [Error] {e}")
                client._reset_data()
    except KeyboardInterrupt:
        print()
    finally:
        client.close()


if __name__ == "__main__":
    from hybrid_ftp.client.transfer import read_file_chunks
    import os
    main()
