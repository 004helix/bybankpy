#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from six.moves import input

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import mtb


def main():
    x = mtb.xcard()

    print('---')
    pwd = input('Enter your new password (digits only, 8 chars: ')
    if len(pwd) != 8 or not pwd.isdigit():
        raise Exception('Bad password, try again')

    pan = input('Enter your x-card number: ')
    cvc = input('Enter your cvc2 code: ')
    r = x.register(pan, cvc)

    # otp request
    otp = input('Enter your SMS code: ')
    o = x.confirmotp(otp.strip())

    # password
    x.setpassword(pwd)

    print('Registered')
    print('---')
    print('password:', pwd)
    print('userId:', r['userId'])
    print('-')
    print('CARDREF (not needed?):', r['CARDREF'])
    print('trsaPub (not nneded?):', o['trsaPub'])


if __name__ == '__main__':
    main()
