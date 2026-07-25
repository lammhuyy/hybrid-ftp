"""Run this AFTER starting run_server.py in another terminal."""

import socket
import sys
import os

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 2121

print(f"Diagnostic: trying to connect to {HOST}:{PORT}")
print()

# 1. DNS resolution
try:
    ips = socket.getaddrinfo(HOST, PORT, socket.AF_INET, socket.SOCK_STREAM)
    print(f"[OK] DNS resolved {HOST} -> {[addr[4][0] for addr in ips]}")
except Exception as e:
    print(f"[FAIL] DNS resolution: {e}")
    sys.exit(1)

# 2. TCP connect with timeout
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
try:
    print(f"Attempting TCP connect to {HOST}:{PORT} (timeout=10s)...")
    s.connect((HOST, PORT))
    print(f"[OK] TCP connected!")
except socket.timeout:
    print(f"[FAIL] TCP connect timed out after 10s")
    print("  Possible causes:")
    print("  - Server not running on that host:port")
    print("  - Firewall blocking inbound TCP 2121")
    print("  - Wrong IP address")
    s.close()
    sys.exit(1)
except ConnectionRefusedError:
    print(f"[FAIL] Connection refused - server not listening on {HOST}:{PORT}")
    s.close()
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    s.close()
    sys.exit(1)

# 3. Read greeting
try:
    print("Reading server greeting...")
    data = s.recv(4096)
    print(f"[OK] Got greeting: {data!r}")
except socket.timeout:
    print(f"[FAIL] Timeout waiting for greeting")
    s.close()
    sys.exit(1)
except Exception as e:
    print(f"[FAIL] Error reading greeting: {e}")
    s.close()
    sys.exit(1)

# 4. Send a command
try:
    s.sendall(b"NOOP\r\n")
    print("[OK] Sent NOOP command")
    data = s.recv(4096)
    print(f"[OK] Response: {data!r}")
except Exception as e:
    print(f"[FAIL] Command exchange: {e}")
    s.close()
    sys.exit(1)

s.close()
print()
print("=== Server is fully reachable and operational ===")
