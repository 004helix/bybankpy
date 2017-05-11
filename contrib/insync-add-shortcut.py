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

    for prodtype in ('ACCOUNT', 'DEPOSIT', 'LOAN'):
        for item in i.products(prodtype)['items']:
            if 'onDesktop' not in item or item['onDesktop']:
                continue
            print('------------------------------------')
            print('    title:', item['info']['title'])
            print('  type/id:', item['type'], item['id'])
            if 'amount' in item['info']:
                print('  balance:',
                      item['info']['amount']['amount'],
                      item['info']['amount']['currency'])

    print()

    type_ = input('Enter item TYPE: ')
    id_ = input('Enter item ID: ')

    i.debug = True
    i.add_product_shortcut(type_.strip(), id_.strip())
    i.debug = False
    i.logout()


if __name__ == '__main__':
    main()
