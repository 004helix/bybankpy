#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals
from six.moves import dbm_gnu as gdbm, input
import uuid
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import insync


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
        print('Device already registered/inactive')
        return

    # Request Passport ID
    login = input('Enter your passport ID: ')

    # auth request
    i.auth(login=login.strip().upper())

    # otp request
    otp = input('Enter your SMS code: ')

    # auth confirm and logout
    i.auth_confirm(otp.strip())
    i.logout()

    print('Registered')


if __name__ == '__main__':
    main()
