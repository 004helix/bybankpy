#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from six.moves import input
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


def main():
    i = insync.client(os.path.expanduser('~/lib/insync.db'))
    i.login()
    i.desktop()

    # transfer 12.00 [account currency] from shortcut id 1000
    # to shortcut id 2000
    #
    # you can get shortcut ids using
    # $ insync-show-desktop.py
    # $ insync-add-shortcut.py
    i.transfer(1000, 2000, 12.0)

    i.logout()


if __name__ == '__main__':
    main()
