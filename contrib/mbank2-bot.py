#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function
from datetime import datetime
import threading
import binascii
import time
import yaml
import json
import sys
import os

import mbank2

try:
    from Queue import Queue, Empty
except:
    from queue import Queue, Empty


mypid = os.getpid()
state = '/dev/shm/mbank2.json'
seqstate = os.path.expanduser('~/lib/mbank2.seq')
with open(os.path.expanduser('~/etc/mbank2.yml'), 'r') as fd:
    conf = yaml.safe_load(fd)

interval = int(conf['interval'])
clientid = int(conf['clientid'])
deviceid = binascii.unhexlify(conf['deviceid'])  # 4 bytes
authkey = binascii.unhexlify(conf['authkey'])  # 32 bytes
cards = conf['cards']


def printlog(*args):
    d = datetime.now().replace(microsecond=0)
    print(d.isoformat(' '), *args)
    sys.stdout.flush()


def rxworker(client, q):
    try:
        while True:
            (seq, cmd, args) = client.read()
            q.put((cmd, args))
    except Exception as e:
        q.put((None, e))


def cmdparser(client, rqs, cmd, args):
    if cmd != 6:
        hexes = binascii.hexlify(args)
        printlog('received unknown command {0}'.format(cmd), hexes)
        return

    cmd6 = client.parse6(args)

    if cmd6[0] not in rqs:
        printlog('received unrequested reply {0}'.format(cmd6[0]), cmd6)
        return

    cardid = rqs[cmd6[0]]
    del rqs[cmd6[0]]

    printlog('card', cardid, cmd6)

    try:
        with open(state, 'r') as fd:
            s = json.loads(fd.read())
    except:
        s = {}

    s[str(cardid)] = {
        'time': int(time.time()),
        'name': cards[cardid],
        'args': cmd6[1:]
    }

    with open('{0}.{1}'.format(state, mypid), 'w') as fd:
        fd.write(json.dumps(s, indent=2, sort_keys=True))

    os.rename('{0}.{1}'.format(state, mypid), state)


def main():
    client = mbank2.client(clientid, deviceid, authkey)

    try:
        with open(seqstate, 'r') as fd:
            client.seq = int(fd.read())
    except:
        pass

    client.connect()

    q = Queue()

    rx = threading.Thread(target=rxworker, args=(client, q))
    rx.daemon = True
    rx.start()

    rqs = {}

    while True:
        if len(rqs) > 64:
            rqs = {}  # overflow

        for cardid in cards.keys():
            seq = client.updatebalance(cardid)
            rqs[seq] = cardid

        with open('{0}.{1}'.format(seqstate, mypid), 'w') as f:
            f.write(str(seq + 1))

        os.rename('{0}.{1}'.format(seqstate, mypid), seqstate)

        while True:
            try:
                (cmd, args) = q.get(timeout=interval)
            except Empty:
                break

            q.task_done()

            if cmd is None:
                raise args

            cmdparser(client, rqs, cmd, args)


if __name__ == '__main__':
    main()
