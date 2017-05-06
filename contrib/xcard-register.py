#!/usr/bin/python

from __future__ import print_function, unicode_literals

import mtb


def main():
    m = mtb.xcard()

    print('---')
    pwd = input('Enter your new password (digits only, 8 chars: ')
    if len(pwd) != 8 or not pwd.isdigit():
        raise Exception('Bad password, try again')

    pan = input('Enter your x-card number: ')
    cvc = input('Enter your cvc2 code: ')
    r = m.register(pan, cvc)

    # otp request
    otp = input('Enter your SMS code: ')
    o = m.confirmotp(otp.strip())

    # password
    m.setpassword(pwd)

    print('Registered')
    print('---')
    print('password:', pwd)
    print('userId:', r['userId'])
    print('-')
    print('CARDREF (not needed?):', r['CARDREF'])
    print('trsaPub (not nneded?):', o['trsaPub'])


if __name__ == '__main__':
    main()
