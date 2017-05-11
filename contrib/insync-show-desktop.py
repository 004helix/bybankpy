#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


def main():
    i = insync.client(os.path.expanduser('~/lib/insync.db'))
    i.login()
    d = i.desktop()

    for shortcut in d['shortcuts']:
        print('------------------------------------')
        print('    title:', shortcut['icon']['title'])
        print('  type/id:', shortcut['objectType'], shortcut['id'])
        if 'tagBalance' in shortcut:
            print('  balance:', shortcut['tagBalance'])


if __name__ == '__main__':
    main()
