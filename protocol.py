import struct

def pack_coords(x, y):
    return struct.pack('hh', int(x), int(y))

def unpack_coords(data):
    return struct.unpack('hh', data)

def recv_all(sock, length):
    content = b""
    while length > 0:
        temp = sock.recv(length)
        if not temp: break
        length -= len(temp)
        content += temp
    return content