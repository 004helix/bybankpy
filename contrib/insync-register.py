#!/usr/bin/python

from __future__ import print_function, unicode_literals
from six.moves import dbm_gnu as gdbm, input

import insync
import uuid


def main():
    print('---')
    path = input('Enter path to insync.db: ')

    db = gdbm.open(path, 'c')

    if b'uuid' in db or b'token' in db:
        print('Device uuid already exists')
        print('Please, create new database')
        return

    db['uuid'] = str(uuid.uuid4())
    db.close()

    i = insync.client(path)
    i.debug = True

    # Check device status
    if i.check_device_status()['status'] != 'NEW':
        print('Device already registered')
        return

    # Request Passport ID
    login = input('Enter your passport ID: ')

    # auth request
    i.auth(login=login.strip().upper())

    # otp request
    otp = input('Enter your SMS code: ')

    # auth confirm
    i.auth_confirm(otp.strip())

    print('Registered')


if __name__ == '__main__':
    main()
