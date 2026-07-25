import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from hybrid_ftp.server.ftp_server import run_server


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hybrid FTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=2121, help="Control port")
    args = parser.parse_args()
    run_server(args.host, args.port)
