#!/usr/bin/env python3
import sys
import struct

def read_spritemap(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print("spritemap.bin is empty.")
        return

    try:
        count, = struct.unpack('>I', data[:4])
        print(f"Sprite Map contains {count} entries:")
        offset = 4
        for _ in range(count):
            key_integer_id, strlen = struct.unpack('>II', data[offset:offset+8])
            offset += 8
            utf8_string_id = data[offset:offset+strlen].decode('utf-8')
            offset += strlen
            print(f"  {key_integer_id}: {utf8_string_id}")
    except (struct.error, IndexError) as e:
        print(f"Error parsing spritemap.bin: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python read_spritemap.py <path_to_spritemap.bin>", file=sys.stderr)
        sys.exit(1)
    
    read_spritemap(sys.argv[1])
