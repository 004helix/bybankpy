#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import insync
import pickle
import json

def main():
    with open('insync.pickle', 'rb') as fd:
        i = pickle.load(fd)

    print(json.dumps(i.summary(), indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
