#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import pickle
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


def main():
    i = insync.client(os.path.expanduser('~/lib/insync.db'))
    i.login()
    i.desktop()

    with open(os.path.expanduser('~/lib/insync.pickle'), 'wb') as fd:
        pickle.dump(i, fd, -1)


if __name__ == '__main__':
    main()
