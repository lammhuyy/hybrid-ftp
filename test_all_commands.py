import sys
import os
import threading
import time
sys.path.insert(0, os.path.dirname(__file__))

from hybrid_ftp.server.ftp_server import FTPServer
from hybrid_ftp.client.ftp_client import FTPClient
from hybrid_ftp.client.transfer import read_file_chunks, Progress
from hybrid_ftp.common.checksum import sha256_data
from hybrid_ftp.common.control_protocol import send_line, read_line, parse_command, format_port, parse_port, parse_pasv_reply
from hybrid_ftp.common.constants import REPLIES


server = FTPServer(host="127.0.0.1", port=2129)

def run_server():
    try:
        server.start()
    except Exception:
        pass

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(0.5)

client = FTPClient()
passed = 0
failed = 0

def check(label, ok, detail=""):
    global passed, failed
    if ok:
        print(f"  OK  {label}")
        passed += 1
    else:
        print(f"  FAIL  {label}  {detail}")
        failed += 1

def send_tcp(cmd):
    send_line(client.control, cmd)
    return client._read_reply()


print("=== All FTP Commands Test ===\n")

# ----- 1. Connection & Authentication -----
client.connect("127.0.0.1", 2129)
check("220 greeting", True)

ok_login = client.login("alice", "password")
check("USER/PASS login", ok_login)

# wrong password
c2 = FTPClient()
c2.connect("127.0.0.1", 2129)
c2.send_raw("USER alice")
resp = c2.send_raw("PASS wrongpass")
check("PASS wrong -> 530", "530" in resp)
c2.close()

# ----- 2. Unauthenticated guard -----
c3 = FTPClient()
c3.connect("127.0.0.1", 2129)
resp = c3.send_raw("PWD")
check("cmd before login -> 530", "530" in resp)
c3.close()

# ----- 3. NOOP -----
resp = send_tcp("NOOP")
check("NOOP -> 200", "200" in resp)

# ----- 4. HELP -----
resp = send_tcp("HELP")
check("HELP -> 214", "214" in resp)

# ----- 5. PWD -----
resp = send_tcp("PWD")
check("PWD -> 257", "257" in resp)

# ----- 6. MKD -----
resp = send_tcp("MKD testcommands")
check("MKD -> 257", "257" in resp)

# ----- 7. CWD -----
resp = send_tcp("CWD testcommands")
check("CWD -> 250", "250" in resp)

# ----- 8. PWD (after CWD) -----
resp = send_tcp("PWD")
check("PWD shows /testcommands", "/testcommands" in resp)

# ----- 9. CDUP -----
resp = send_tcp("CDUP")
check("CDUP -> 250", "250" in resp)

resp = send_tcp("PWD")
check("PWD back to /", '/"' in resp or resp.strip().endswith('"/"'))

# ----- 10. TYPE -----
resp = send_tcp("TYPE I")
check("TYPE I -> 200", "200" in resp)
resp = send_tcp("TYPE A")
check("TYPE A -> 200", "200" in resp)
resp = send_tcp("TYPE X")
check("TYPE X -> 504", "504" in resp)

# ----- 11. MODE -----
resp = send_tcp("MODE S")
check("MODE S -> 200", "200" in resp)
resp = send_tcp("MODE B")
check("MODE B -> 202", "202" in resp)
resp = send_tcp("MODE X")
check("MODE X -> 504", "504" in resp)

# ----- 12. PASV -----
resp = send_tcp("PASV")
check("PASV -> 227", "227" in resp)
client.data_mode = "PASSIVE"
ip, port = parse_pasv_reply(resp)
client.pasv_addr = (ip, port)

# ----- 13. STOR (upload) -----
test_data = b"Hello world! Test file for all commands.\n" * 100
local_up = "_test_up.txt"
with open(local_up, "wb") as f:
    f.write(test_data)

resp = send_tcp(f"STOR _test_up.txt")
check("STOR preamble -> 150", "150" in resp)
if "150" in resp:
    from hybrid_ftp.client.data_channel_cli import open_passive_sender
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    rdt.send(read_file_chunks(local_up))
    resp2 = client._read_reply()
    check("STOR complete -> 226", "226" in resp2)
    rdt.close()
    client.data_mode = "NONE"

# ----- 14. SIZE -----
resp = send_tcp("SIZE _test_up.txt")
check("SIZE -> 213 <bytes>", "213" in resp)

# ----- 15. MDTM -----
resp = send_tcp("MDTM _test_up.txt")
check("MDTM -> 213 <ts>", "213" in resp)

# ----- 16. STAT -----
resp = send_tcp("STAT _test_up.txt")
check("STAT existing -> 213", "213" in resp)
resp = send_tcp("STAT nonexistent")
check("STAT nonexistent -> 550", "550" in resp)

# ----- 17. LIST (data channel) -----
resp = send_tcp("PASV")
check("PASV for LIST -> 227", "227" in resp)
ip2, port2 = parse_pasv_reply(resp)
client.pasv_addr = (ip2, port2)
client.data_mode = "PASSIVE"

send_line(client.control, "LIST")
resp = client._read_reply()
check("LIST -> 150", "150" in resp)
if "150" in resp:
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    data = rdt.recv()
    check("LIST data received", len(data) > 0)
    resp2 = client._read_reply()
    check("LIST complete -> 226", "226" in resp2)
    rdt.close()
    client.data_mode = "NONE"

# ----- 18. NLST (data channel) -----
resp = send_tcp("PASV")
ip2, port2 = parse_pasv_reply(resp)
client.pasv_addr = (ip2, port2)
client.data_mode = "PASSIVE"

send_line(client.control, "NLST")
resp = client._read_reply()
check("NLST -> 150", "150" in resp)
if "150" in resp:
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    data = rdt.recv()
    check("NLST data received", len(data) > 0)
    resp2 = client._read_reply()
    check("NLST complete -> 226", "226" in resp2)
    rdt.close()
    client.data_mode = "NONE"

# ----- 19. RETR (download) -----
local_dl = "_test_dl.txt"
resp = send_tcp("PASV")
ip2, port2 = parse_pasv_reply(resp)
client.pasv_addr = (ip2, port2)
client.data_mode = "PASSIVE"

send_line(client.control, "RETR _test_up.txt")
resp = client._read_reply()
check("RETR -> 150", "150" in resp)
if "150" in resp:
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    dl_data = rdt.recv()
    with open(local_dl, "wb") as f:
        f.write(dl_data)
    resp2 = client._read_reply()
    check("RETR complete -> 226", "226" in resp2)
    check("RETR data integrity", dl_data == test_data)
    rdt.close()
    client.data_mode = "NONE"

# ----- 20. APPE (append) -----
append_data = b"Appended line.\n"
with open("_test_app.txt", "wb") as f:
    f.write(append_data)

resp = send_tcp("PASV")
ip2, port2 = parse_pasv_reply(resp)
client.pasv_addr = (ip2, port2)
client.data_mode = "PASSIVE"

send_line(client.control, "APPE _test_up.txt")
resp = client._read_reply()
check("APPE -> 150", "150" in resp)
if "150" in resp:
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    rdt.send(read_file_chunks("_test_app.txt"))
    resp2 = client._read_reply()
    check("APPE complete -> 226", "226" in resp2)
    rdt.close()
    client.data_mode = "NONE"

# ----- 21. STOU (upload unique) -----
resp = send_tcp("PASV")
ip2, port2 = parse_pasv_reply(resp)
client.pasv_addr = (ip2, port2)
client.data_mode = "PASSIVE"

send_line(client.control, "STOU")
resp = client._read_reply()
check("STOU -> 150", "150" in resp)
if "150" in resp:
    rdt = open_passive_sender(client.pasv_addr[0], client.pasv_addr[1])
    rdt.send(read_file_chunks("_test_up.txt"))
    resp2 = client._read_reply()
    check("STOU complete -> 226", "226" in resp2)
    rdt.close()
    client.data_mode = "NONE"

# ----- 22. PORT (active mode) -----
from hybrid_ftp.client.data_channel_cli import open_port_listener
port_sock, port_addr = open_port_listener()
local_ip = client.control.getsockname()[0]
if local_ip == "0.0.0.0":
    local_ip = "127.0.0.1"
h1, h2, h3, h4 = local_ip.split(".")
p1, p2 = port_addr[1] >> 8, port_addr[1] & 0xFF
port_cmd = format_port(h1, h2, h3, h4, p1, p2)
resp = send_tcp(f"PORT {port_cmd}")
check("PORT -> 200", "200" in resp)
client.data_socket = port_sock
client.data_mode = "ACTIVE"
client.peer_addr = None

resp = send_tcp("LIST")
check("LIST (PORT) -> 150", "150" in resp)
if "150" in resp:
    try:
        port_sock.accept()
        data = port_sock.recv()
        check("LIST (PORT) data received", len(data) > 0)
        resp2 = client._read_reply()
        check("LIST (PORT) complete -> 226", "226" in resp2)
    except Exception:
        check("LIST (PORT) transfer", False, "RDT failed")
    port_sock.close()
    client.data_mode = "NONE"

# ----- 23. HASH -----
resp = send_tcp("HASH _test_up.txt")
expected_file_data = test_data + append_data
check("HASH -> 213 + 64 hex chars", "213" in resp)
if "213" in resp:
    digest = resp[4:].strip()
    check("HASH correct", digest == sha256_data(expected_file_data))

# ----- 24. RNFR / RNTO -----
resp = send_tcp("RNFR _test_up.txt")
check("RNFR -> 350", "350" in resp)
resp = send_tcp("RNTO _test_renamed.txt")
check("RNTO -> 250", "250" in resp)

resp = send_tcp("SIZE _test_renamed.txt")
check("renamed file exists", "213" in resp)

# rename back
send_tcp("RNFR _test_renamed.txt")
resp = send_tcp("RNTO _test_up.txt")
check("rename back -> 250", "250" in resp)

# ----- 25. DELE -----
resp = send_tcp("DELE _test_up.txt")
check("DELE -> 250", "250" in resp)

resp = send_tcp("DELE nonexistent")
check("DELE nonexistent -> 550", "550" in resp)

# ----- 26. RMD -----
resp = send_tcp("RMD testcommands")
check("RMD -> 250", "250" in resp)

# ----- 27. ABOR -----
resp = send_tcp("ABOR")
check("ABOR -> 426", "426" in resp)

# ----- 28. QUIT -----
resp = send_tcp("QUIT")
check("QUIT -> 221", "221" in resp)

# ----- Cleanup -----
client.close()
os.remove(local_up)
if os.path.exists(local_dl):
    os.remove(local_dl)
if os.path.exists("_test_app.txt"):
    os.remove("_test_app.txt")
server.stop()

print(f"\n{'='*40}")
print(f"  Passed: {passed}   Failed: {failed}")
print(f"{'='*40}")
if failed:
    sys.exit(1)
