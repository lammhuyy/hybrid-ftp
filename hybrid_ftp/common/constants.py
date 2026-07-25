import struct

MAGIC = 0xF7D0
HEADER_FMT = "!HIIBHHI"
HEADER_SIZE = 19

MAX_PAYLOAD = 1024

INITIAL_RTO_MS = 300
MIN_RTO_MS = 100
MAX_RTO_MS = 4000
INITIAL_CWND = 1
MAX_WINDOW = 32
IDLE_SESSION_TIMEOUT_S = 300
HANDSHAKE_TIMEOUT_S = 30
TRANSFER_IDLE_TIMEOUT_S = 30

TCP_PORT = 2121

REPLIES = {
    150: "150 Opening BINARY mode data connection for {file} ({size} bytes).\r\n",
    151: "151 Opening ASCII mode data connection for {file} ({size} bytes).\r\n",
    200: "200 Command okay.\r\n",
    202: "202 Command not implemented, superfluous at this site.\r\n",
    211: "211 System status, or system help reply.\r\n",
    213: "213 {value}\r\n",
    214: "214-The following commands are recognized:\r\n  USER PASS QUIT NOOP PWD CWD CDUP MKD RMD LIST NLST STAT\r\n  SIZE MDTM TYPE MODE PORT PASV RETR STOR STOU APPE DELE\r\n  RNFR RNTO HASH ABOR HELP\r\n214 End of HELP.\r\n",
    220: "220 Hybrid FTP Server ready.\r\n",
    221: "221 Service closing control connection.\r\n",
    226: "226 Transfer complete.\r\n",
    227: "227 Entering Passive Mode ({h1},{h2},{h3},{h4},{p1},{p2}).\r\n",
    230: "230 User {user} logged in, proceed.\r\n",
    250: "250 Requested file action okay, completed.\r\n",
    257: '257 "{path}" created.\r\n',
    331: "331 User name okay, need password.\r\n",
    332: "332 Need account for login.\r\n",
    350: "350 Requested file action pending further information.\r\n",
    421: "421 Service not available, closing control connection.\r\n",
    425: "425 Can't open data connection.\r\n",
    426: "426 Connection closed; transfer aborted.\r\n",
    450: "450 Requested file action not taken.\r\n",
    451: "451 Requested action aborted: local error in processing.\r\n",
    500: "500 Syntax error, command unrecognized.\r\n",
    501: "501 Syntax error in parameters or arguments.\r\n",
    502: "502 Command not implemented.\r\n",
    503: "503 Bad sequence of commands.\r\n",
    504: "504 Command not implemented for that parameter.\r\n",
    530: "530 Not logged in.\r\n",
    550: "550 Requested action not taken. {reason}\r\n",
    553: "553 Requested action not taken. File name not allowed.\r\n",
}
