import struct
import zlib
from .constants import MAGIC, HEADER_FMT, HEADER_SIZE, MAX_PAYLOAD, FLAG_DATA, FLAG_ACK, FLAG_SYN, FLAG_FIN, FLAG_NACK, FLAG_LAST


def pack_header(seq_num=0, ack_num=0, flags=FLAG_DATA, window=32, length=0, checksum=0):
    return struct.pack(HEADER_FMT, MAGIC, seq_num, ack_num, flags, window, length, checksum)


def unpack_header(data):
    if len(data) < HEADER_SIZE:
        raise ValueError(f"Data too short for header: {len(data)} < {HEADER_SIZE}")
    magic, seq_num, ack_num, flags, window, length, checksum = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic:#06x} != {MAGIC:#06x}")
    return {
        "magic": magic,
        "seq_num": seq_num,
        "ack_num": ack_num,
        "flags": flags,
        "window": window,
        "length": length,
        "checksum": checksum,
    }


def compute_checksum(header_no_crc, payload):
    return zlib.crc32(header_no_crc + payload) & 0xFFFFFFFF


def build_packet(seq_num=0, ack_num=0, flags=FLAG_DATA, window=32, payload=b""):
    payload = bytes(payload)
    length = len(payload)
    header_no_crc = struct.pack(HEADER_FMT, MAGIC, seq_num, ack_num, flags, window, length, 0)
    checksum = compute_checksum(header_no_crc, payload)
    header = struct.pack(HEADER_FMT, MAGIC, seq_num, ack_num, flags, window, length, checksum)
    return header + payload


def parse_packet(data):
    hdr = unpack_header(data)
    payload = data[HEADER_SIZE:HEADER_SIZE + hdr["length"]]
    checksum_field = hdr["checksum"]

    header_no_crc = struct.pack(HEADER_FMT, MAGIC, hdr["seq_num"], hdr["ack_num"], hdr["flags"], hdr["window"], hdr["length"], 0)
    expected_crc = compute_checksum(header_no_crc, payload)
    if checksum_field != expected_crc:
        raise ValueError(f"CRC mismatch: packet corrupted")
    hdr["payload"] = payload
    return hdr


def has_flag(flags, flag):
    return (flags & flag) != 0
