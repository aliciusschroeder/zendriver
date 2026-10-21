import zlib, struct
def decode_png(data: bytes):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8; idat = b''; w = h = 0; ctype = None; depth = None
    while pos < len(data):
        ln, = struct.unpack('>I', data[pos:pos+4]); typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+ln]; pos += 12 + ln
        if typ == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', chunk[:10])
        elif typ == b'IDAT':
            idat += chunk
        elif typ == b'IEND':
            break
    assert depth == 8, depth
    bpp = {2: 3, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows = []; prev = bytearray(stride); i = 0
    for y in range(h):
        f = raw[i]; i += 1
        line = bytearray(raw[i:i+stride]); i += stride
        for x in range(stride):
            a = line[x-bpp] if x >= bpp else 0
            b = prev[x]; c = prev[x-bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c; pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        rows.append(line); prev = line
    def px(x, y):
        o = x * bpp
        return tuple(rows[y][o:o+3])
    return w, h, px
