# -*- coding: utf-8 -*-
#
# Crazy mbank2 structs
#

from struct import pack, unpack
from datetime import datetime
import sys

if sys.version_info[0] == 3:
    unichr = chr


def packint(i):
    data = []

    while True:
        if i > 0x7f:
            data.append(pack('B', 0x80 | (i & 0x7f)))
            i >>= 7
        else:
            data.append(pack('B', i))
            break

    return b''.join(data)


def packbytes(*args):
    data = []

    for arg in args:
        data.append(packint(len(arg)))
        data.append(arg)

    return b''.join(data)


def packdate(ts):
    date = datetime.utcfromtimestamp(ts)

    # year, 7 bits
    out = (max(2000, date.year) % 100) & 0x7f

    # month, 4 bits
    out <<= 4
    out |= (date.month - 1) & 0x0f

    # day, 5 bits
    out <<= 5
    out |= date.day & 0x1f

    # hour, 5 bits
    out <<= 5
    out |= date.hour & 0x1f

    # minute, 6 bits
    out <<= 6
    out |= date.minute & 0x3f

    # second/2, 5 bits
    out <<= 5
    out |= int(date.second / 2) & 0x1f

    return pack('!I', out)


class parser:
    def __init__(self, data):
        bits = []

        for byte in data:
            if not isinstance(byte, int):
                (byte,) = unpack('B', byte)
            bits.append('{0:08b}'.format(byte).encode())

        self.bits = b''.join(bits)

    def bytes(self):
        data = []

        if len(self.bits) % 8:
            self.bits += b'0' * (8 - (len(self.bits) % 8))

        for i in range(0, len(self.bits), 8):
            data.append(pack('B', int(self.bits[i:i + 8], 2)))

        return b''.join(data)

    def getint(self):
        i = 0
        n = 0
        while True:
            byte = int(self.bits[0:8], 2)
            self.bits = self.bits[8:]

            i |= (byte & 0x7f) << (7 * n)
            if byte < 0x80:
                break

            n += 1

        return i

    def getslimint(self):
        if self.bits[:1] == b'1':
            i = int(self.bits[1:5], 2)
            self.bits = self.bits[5:]
            return i

        self.bits = self.bits[1:]
        return self.getint()

    def getbool(self):
        bit = self.bits[:1]
        self.bits = self.bits[1:]
        return (bit == b'1')

    def getbits(self, n):
        i = int(self.bits[:n], 2)
        self.bits = self.bits[n:]
        return i

    def getbytes(self):
        data = []
        length = self.getint()

        for i in range(0, length * 8, 8):
            data.append(pack('B', int(self.bits[i:i + 8], 2)))

        self.bits = self.bits[length * 8:]
        return b''.join(data)

    def getstr(self):
        data = u''
        length = self.getint()

        for i in range(0, length * 8, 8):
            c = int(self.bits[i:i + 8], 2)
            if c > 127:
                data += unichr(c + 1024 - 128)
            else:
                data += unichr(c)

        self.bits = self.bits[length * 8:]
        return data
