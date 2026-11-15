"""ATF1508AS TQFP-100 pin map, transcribed from Microchip DS20006682A Tables 2-1/2-2.

Datasheet errata handled here (cross-checked against the TQFP-100 pin diagram, p.3):
  * Table 2-2 lists MC8 as 'A/TDI' at TQFP 98; TDI is MC32 at pin 4. MC8 is plain I/O.
  * Table 2-2 gives MC17 no TQFP pin; PQFP 16 -> TQFP 14 (pin 14 is I/O on the diagram).
  * Table 2-2 lists MC94 at TQFP 62, the same as MC96/TCK. Pin 61 is otherwise unused -> MC94 = 61.
"""
DEDICATED = {
    90: 'IN_OE2_GCLK2', 89: 'IN_GCLR', 88: 'IN_OE1', 87: 'IN_GCLK1',
}
GND = [11, 26, 38, 43, 59, 74, 86, 95]
VCCINT = [39, 91]
VCCIO = [3, 18, 34, 51, 66, 82]
# macrocell -> TQFP pin (None = buried)
MC = {
 1:2, 3:1, 5:100, 6:99, 8:98, 9:97, 11:96, 13:94, 14:93, 16:92,
 17:14, 19:13, 21:12, 22:10, 24:9, 25:8, 27:7, 29:6, 30:5, 32:4,
 33:25, 35:24, 37:23, 38:22, 40:21, 41:20, 43:19, 45:17, 46:16, 48:15,
 49:37, 51:36, 53:35, 54:33, 56:32, 57:31, 59:30, 61:29, 62:28, 64:27,
 65:40, 67:41, 69:42, 70:44, 72:45, 73:46, 75:47, 77:48, 78:49, 80:50,
 81:52, 83:53, 85:54, 86:55, 88:56, 89:57, 91:58, 93:60, 94:61, 96:62,
 97:63, 99:64, 101:65, 102:67, 104:68, 105:69, 107:70, 109:71, 110:72, 112:73,
 113:75, 115:76, 117:77, 118:78, 120:79, 121:80, 123:81, 125:83, 126:84, 128:85,
}
SPECIAL = {1: 'PD1', 4: 'TDI', 15: 'TMS', 62: 'TCK', 73: 'TDO', 41: 'PD2', 85: 'GCLK3'}


def pinmap():
    m = {}
    for p in GND: m[p] = ('GND', 'power_in')
    for p in VCCINT: m[p] = ('VCCINT', 'power_in')
    for p in VCCIO: m[p] = ('VCCIO', 'power_in')
    for p, n in DEDICATED.items(): m[p] = (n, 'input')
    for mc, p in MC.items():
        assert p not in m, (mc, p, m.get(p))
        blk = 'ABCDEFGH'[(mc - 1) // 16]
        name = 'IO%d_%s' % (mc, blk)
        if p in SPECIAL: name += '_' + SPECIAL[p]
        m[p] = (name, 'bidirectional')
    return m


if __name__ == '__main__':
    m = pinmap()
    missing = [p for p in range(1, 101) if p not in m]
    print('pins mapped:', len(m), 'missing:', missing)
    print('user I/O:', sum(1 for v in m.values() if v[0].startswith('IO')))
