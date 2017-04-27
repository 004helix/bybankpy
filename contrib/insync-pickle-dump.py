#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import insync
import pickle

def main():
    i = insync.client('insync.db')
    i.login()
    i.desktop()

    with open('insync.pickle', 'wb') as fd:
        pickle.dump(i, fd, -1)

if __name__ == '__main__':
    main()
