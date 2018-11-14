#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


def main():
    i = insync.client(os.path.expanduser('~/lib/insync.db'))
    i.login()
    d = i.desktop()
    s = i.summary()
    i.logout()

    print(json.dumps(s, indent=4))

if __name__ == '__main__':
    main()
