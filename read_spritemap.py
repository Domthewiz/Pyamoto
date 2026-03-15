#!/usr/bin/env python3
import sys
import struct
from id_manager import SpritemapVersion

# TODO: Make this a window in the GUI
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
        if len(data) < 8:
            raise ValueError("Data too short for header")

        version, count = struct.unpack('>II', data[:8])
        
        if version != SpritemapVersion:
            print(f"Warning: Expected SpritemapVersion {SpritemapVersion}, but got {version}.", file=sys.stderr)

        print(f"Sprite Map (Version {version}) contains {count} entries:")
        
        if count == 0:
            return

        offset_table_start = 8
        offsets = []
        for i in range(count):
            ptr = offset_table_start + (i * 4)
            str_offset, = struct.unpack('>I', data[ptr:ptr+4])
            offsets.append(str_offset)

        current_id = 0xF000 

        for offset in offsets:
            if offset >= len(data):
                raise IndexError(f"String offset 0x{offset:X} is out of bounds")

            null_terminator_index = data.find(b'\x00', offset)
            if null_terminator_index == -1:
                raise ValueError("Malformed spritemap entry: missing null terminator")

            utf8_string_id = data[offset:null_terminator_index].decode('utf-8')
            
            print(f"  {current_id} (0x{current_id:04X}): {utf8_string_id}")
            
            current_id += 1

    except (struct.error, IndexError, ValueError, UnicodeDecodeError) as e:
        print(f"Error parsing spritemap.bin: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python read_spritemap.py <path_to_spritemap.bin>", file=sys.stderr)
        sys.exit(1)
    
    read_spritemap(sys.argv[1])
