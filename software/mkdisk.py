"""Minimal ProDOS 140K data-disk builder/reader (from cstodd/Laser128EX-Expansion software/rev01/mkdisk.py).

build_image(volname, [(name, filetype, aux, data), ...]) -> bytes; read_image(img) -> {name: (type, aux, data)}.
The image is a data disk (not bootable): boot ProDOS from another disk, then use this one.
"""
import struct

BLOCKS = 280


def prodos_name(s):
    return s.upper().encode()[:15].ljust(15, b'\0')


def build_image(volname, files):
    img = bytearray(512 * BLOCKS)
    used = set(range(0, 7))                            # boot 0-1, directory 2-5, bitmap 6
    nxt = [7]

    def alloc():
        while nxt[0] in used:
            nxt[0] += 1
        used.add(nxt[0])
        return nxt[0]

    def put(block, data):
        img[block * 512:block * 512 + len(data)] = data

    entries = []
    for name, ftype, aux, data in files:
        if len(data) <= 512:
            key = alloc(); put(key, data); storage, nblk = 1, 1
        else:
            key = alloc()
            blocks = [alloc() for _ in range((len(data) + 511) // 512)]
            idx = bytearray(512)
            for k, b in enumerate(blocks):
                put(b, data[k * 512:(k + 1) * 512])
                idx[k], idx[256 + k] = b & 255, b >> 8
            put(key, idx)
            storage, nblk = 2, len(blocks) + 1
        e = bytearray(39)
        e[0] = (storage << 4) | len(name)
        e[1:16] = prodos_name(name)
        e[16] = ftype
        struct.pack_into('<HH', e, 17, key, nblk)
        e[21:24] = struct.pack('<I', len(data))[:3]
        e[30] = 0xE3                                   # access: destroy/rename/write/read
        struct.pack_into('<H', e, 31, aux)
        struct.pack_into('<H', e, 37, 2)               # header pointer: volume directory key
        entries.append(e)

    # volume directory blocks 2-5 (13 entries per block; first entry = volume header)
    hdr = bytearray(39)
    hdr[0] = 0xF0 | len(volname)
    hdr[1:16] = prodos_name(volname)
    hdr[30], hdr[31], hdr[32] = 0xC3, 0x27, 0x0D
    struct.pack_into('<HHH', hdr, 33, len(entries), 6, BLOCKS)
    slots = [hdr] + entries
    assert len(slots) <= 4 * 13
    for k, blk in enumerate(range(2, 6)):
        d = bytearray(512)
        struct.pack_into('<HH', d, 0, blk - 1 if blk > 2 else 0, blk + 1 if blk < 5 else 0)
        for j in range(13):
            s = k * 13 + j
            if s < len(slots):
                d[4 + j * 39:4 + (j + 1) * 39] = slots[s]
        put(blk, d)
    bm = bytearray(512)                                # 1 = free
    for b in range(BLOCKS):
        if b not in used:
            bm[b >> 3] |= 0x80 >> (b & 7)
    put(6, bm)
    return bytes(img)


def read_image(img):
    """Independent reader used to verify the image."""
    files = {}
    blk = 2
    first = True
    while blk:
        d = img[blk * 512:(blk + 1) * 512]
        nxt = struct.unpack_from('<H', d, 2)[0]
        for j in range(13):
            e = d[4 + j * 39:4 + (j + 1) * 39]
            if first and j == 0:
                assert e[0] >> 4 == 0xF and struct.unpack_from('<H', e, 35)[0] == 6
                continue
            st, nl = e[0] >> 4, e[0] & 15
            if st == 0:
                continue
            name = e[1:1 + nl].decode()
            key = struct.unpack_from('<H', e, 17)[0]
            eof = e[21] | (e[22] << 8) | (e[23] << 16)
            if st == 1:
                data = img[key * 512:key * 512 + eof]
            else:
                idx = img[key * 512:(key + 1) * 512]
                data = b''.join(img[(idx[k] | (idx[256 + k] << 8)) * 512:][:512]
                                for k in range((eof + 511) // 512))[:eof]
            files[name] = (e[16], struct.unpack_from('<H', e, 31)[0], data)
        first = False
        blk = nxt
    return files
