#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
import insync
import json

def main():
    i = insync.client('insync.db')
    i.debug = True
    i.login()
    i.desktop()

    h = insync.history(i, 'history.db')

    # reload all history
    h.reload()

    # check transaction type of each element
    for item in h:
        tt = h.get_type(item)
        print(tt, item['info']['title'])

    # done
    h.close()

    i.logout()

if __name__ == '__main__':
    main()
