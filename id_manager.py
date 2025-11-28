# Sprite ID Manager for dynamic string<->integer ID mapping
# Handles the allocation of integer IDs for custom sprites identified by strings

import globals
import struct

class SpriteIDManager:
    def __init__(self):
        self.reset()

    def reset(self):
        self.string_to_int = {}
        self.int_to_string = {}
        self.next_free_id = 1000

    def load_from_binary(self, data: bytes):
        self.reset()
        if not data:
            return

        try:
            count, = struct.unpack('>I', data[:4])
            offset = 4
            for _ in range(count):
                key_integer_id, = struct.unpack('>I', data[offset:offset+4])
                offset += 4

                null_terminator_index = data.find(b'\x00', offset)
                if null_terminator_index == -1:
                    raise ValueError("Malformed spritemap entry: missing null terminator")

                utf8_string_id = data[offset:null_terminator_index].decode('utf-8')
                offset = null_terminator_index + 1

                if utf8_string_id and key_integer_id >= 1000:
                    self.string_to_int[utf8_string_id] = key_integer_id
                    self.int_to_string[key_integer_id] = utf8_string_id
                    if key_integer_id >= self.next_free_id:
                        self.next_free_id = key_integer_id + 1
                    
                    if utf8_string_id in globals.CustomSpriteDefinitions:
                        while len(globals.Sprites) <= key_integer_id:
                            globals.Sprites.append(None)
                        globals.Sprites[key_integer_id] = globals.CustomSpriteDefinitions[utf8_string_id]
        except (struct.error, IndexError, ValueError) as e:
            print(f"Error parsing spritemap.bin: {e}")
            self.reset()

    def get_save_data_binary(self) -> bytes:
        if not self.string_to_int:
            return b""

        data = bytearray()
        data.extend(struct.pack('>I', len(self.string_to_int)))

        for str_id, int_id in sorted(self.string_to_int.items()):
            encoded_str_id = str_id.encode('utf-8') + b'\x00'
            
            data.extend(struct.pack('>I', int_id))
            data.extend(encoded_str_id)
        
        return bytes(data)

    def get_id_for_string(self, str_id: str) -> int:
        if str_id in self.string_to_int:
            return self.string_to_int[str_id]

        if str_id not in globals.CustomSpriteDefinitions:
            raise ValueError(f"Unknown custom sprite string_id: {str_id}")

        new_id = self.next_free_id
        self.next_free_id += 1

        self.string_to_int[str_id] = new_id
        self.int_to_string[new_id] = str_id

        while len(globals.Sprites) <= new_id:
            globals.Sprites.append(None)

        globals.Sprites[new_id] = globals.CustomSpriteDefinitions[str_id]

        return new_id
