#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import pickle
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


def main():
    with open(os.path.expanduser('~/lib/insync.pickle'), 'rb') as fd:
        i = pickle.load(fd)

    os.unlink(os.path.expanduser('~/lib/insync.pickle'))

    print(json.dumps(i.summary(), indent=4, sort_keys=True))

    i.logout()


if __name__ == '__main__':
    main()
