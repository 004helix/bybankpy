# -*- coding: utf-8 -*-
#
# ASB Belarusbank mbank client
#

from __future__ import print_function
from .bits import parser, packint, packbytes, packdate
from struct import pack, unpack
from Crypto.Cipher import AES
import random
import socket
import zlib
import time


class MBankException(Exception):
    pass


class client:
    host = 'gprs.m-bank.by'
    port = 16200

    seq = 3
    recvseq = 0
    sendseq = 0

    iv = b'\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0'

    def __init__(self, clientid, deviceid, authkey):
        self.clientid = clientid
        self.deviceid = deviceid
        self.authkey = authkey

    def sendall(self, data):
        self.s.sendall(data)

    def recvall(self, size):
        data = []

        while size > 0:
            data.append(self.s.recv(size))
            received = len(data[-1])
            if received == 0:
                raise MBankException("Connection closed")
            size -= received

        return b''.join(data)

    # packet sender
    def send(self, data, seq=None):
        if seq is not None:
            sendseq = pack('!i', seq)
        else:
            sendseq = pack('!i', self.sendseq)
            self.sendseq += 1

        size = pack('!H', len(data))
        self.sendall(size + sendseq + data)

    # packet receiver
    def recv(self):
        (size,) = unpack('!H', self.recvall(2))

        if self.recvseq == 0:
            recvseq = 0
        else:
            (recvseq,) = unpack('!i', self.recvall(4))

        self.recvseq += 1

        if size > 0:
            return (recvseq, self.recvall(size))
        else:
            return (recvseq, None)

    # special stupid non-zero randoms
    def randoms(self, size):
        data = [pack('B', random.randint(1, 255)) for _ in range(0, size)]
        return b''.join(data)

    # encrypt data
    def encrypt(self, key, data):
        aes = AES.new(key, AES.MODE_CBC, self.iv)
        out = []

        size = AES.block_size * (int((len(data) + 4) / AES.block_size) + 1)
        out.append(self.randoms(size - len(data) - 5))
        out.append(b'\0')
        out.append(data)
        crc32 = zlib.crc32(b''.join(out)) & 0xffffffff
        out.append(pack('!I', crc32))

        return aes.encrypt(b''.join(out))

    # decrypt data
    def decrypt(self, key, data):
        aes = AES.new(key, AES.MODE_CBC, self.iv)
        data = aes.decrypt(data)

        (crc32,) = unpack('!I', data[-4:])
        if crc32 != zlib.crc32(data[:-4]) & 0xffffffff:
            raise MBankException('Bad checksum')

        return data[data.index(b'\0') + 1:-4]

    # connect to server and authenticate
    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(20)
        self.s.connect((self.host, self.port))

        # receive server handshake (server randoms)
        (n, server_randoms) = self.recv()

        # send client handshake
        my_randoms = self.randoms(4)
        data = packbytes(server_randoms, self.deviceid, my_randoms)
        data = self.encrypt(self.authkey, data)
        self.send(packint(self.clientid) + packbytes(data))

        # receive server reply (with session key)
        (n, data) = self.recv()
        p = parser(self.decrypt(self.authkey, data))
        my_randoms2 = p.getbytes()
        self.sesskey = p.getbytes()

        # check server reply
        if my_randoms != my_randoms2:
            raise MBankException('Bad server reply')

        # increase socket timeout
        self.s.settimeout(60)

        return

    # update balance request
    def updatebalance(self, cardid):
        self.seq += 1
        seq = self.seq
        opts = packint(seq)
        opts += packint(0)     # m6656A(), IDK
        opts += packint(5055)  # m6685b(), IDK, yet another fucking magic
        opts += b'\x42\x10'    # bits 0      -> bit(c.m6685() == null)  = 0
                               # bits 10000  -> slimInt(f)              = 0
                               # bits 10000  -> slimInt(c.m6721z())     = 0
                               # bits 10000  -> slimInt(g.length)       = 0
                               # total 16 bits: 0x4210
        opts += packint(cardid)
        opts += b'\0'          # bits 0        -> bit(z) = 0
                               # bits 0000000  -> padding

        command = packint(6)
        command += packbytes(opts)

        self.seq += 1
        data = packint(self.seq)
        data += packbytes(self.deviceid)
        data += packdate(time.time())
        data += packbytes(command)

        self.send(self.encrypt(self.sesskey, data))
        return seq

    # parse reply type 6
    def parse6(self, data):
        p = parser(data)
        reply = []

        # seq
        reply.append(p.getint())

        p.getslimint()
        i = p.getslimint()

        if i == 8:
            # error?
            reply.append(p.getstr())
            return reply

        if i not in (2, 3, 4):
            raise MBankException('parse6: bad i')

        shouldbefalse = p.getbool()
        p = parser(p.getbytes())

        if shouldbefalse:
            # m6521a
            reply.append('non-packed data not supported')
        else:
            # m6522a
            p.getbool()
            p.getslimint()
            p.getslimint()
            i = p.getslimint()

            for _ in range(0, i):
                t = p.getbits(2)
                if t == 2:
                    reply.append(u'<2:{0}>'.format(p.getslimint()))
                elif t == 1:
                    reply.append(u'<1:{0}>'.format(p.getslimint()))
                elif t == 0:
                    reply.append(p.getstr())
                else:
                    raise MBankException('parse6: unknown type')

            p.getbytes()

        return reply

    # read next packet
    def read(self):
        while True:
            (n, data) = self.recv()
            if data is None:
                # ping -> pong
                self.send(b'', -1)
                continue

            # ack
            self.send(b'', n)

            # decrypt
            data = self.decrypt(self.sesskey, data)

            # parse
            p = parser(data)
            seq = p.getint()
            cmd = p.getint()
            args = p.getbytes()

            return (seq, cmd, args)

    #def pprint(self, prefix, data):
    #    import binascii
    #    p = binascii.hexlify(data)
    #    p = [p[i:i+2].decode('utf-8') for i in range(0, len(p), 2)]
    #    p = ' '.join(p)
    #    print(prefix + p)
