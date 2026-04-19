cdef extern from "FastYZ/fastyz.h":
    int yaz0_compress(const void* input, int length, void* output)
    int yaz0_decompress(const void* input, int length, void* output, int maxout)
    unsigned int yaz0_get_decompressed_size(const void* input)
    int yaz0_is_valid(const void* input)

def is_valid(bytes data) -> bool:
    cdef const unsigned char* c_data = data
    return yaz0_is_valid(<const void*>c_data) != 0

def get_decompressed_size(bytes data) -> int:
    cdef const unsigned char* c_data = data
    if not is_valid(data):
        raise ValueError("Invalid Yaz0 header.")
    return yaz0_get_decompressed_size(<const void*>c_data)

def decompress(bytes data) -> bytes:
    cdef const unsigned char* c_data = data
    if not is_valid(data):
        raise ValueError("Invalid Yaz0 header")
        
    cdef int length = len(data)
    cdef unsigned int dec_size = yaz0_get_decompressed_size(<const void*>c_data)
    cdef bytearray output = bytearray(dec_size)
    cdef char* out_ptr = output
    cdef int result = yaz0_decompress(<const void*>c_data, length, <void*>out_ptr, dec_size)
    
    if result < 0:
        raise RuntimeError(f"Decompression failed with error code: {result}")
        
    return bytes(output)

def compress(bytes data) -> bytes:
    cdef const unsigned char* c_data = data
    cdef int length = len(data)
    cdef int max_out_size = length + (length // 8) + 32 
    cdef bytearray output = bytearray(max_out_size)
    cdef char* out_ptr = output
    cdef int compressed_size = yaz0_compress(<const void*>c_data, length, <void*>out_ptr)
    
    if compressed_size <= 0:
        raise RuntimeError("Compression failed")
        
    return bytes(output[:compressed_size])
