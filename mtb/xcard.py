# -*- coding: utf-8 -*-
#
# MTB X-CARD API
#

from __future__ import print_function, unicode_literals

import requests
import string
import random
import json


class XCardException(Exception):
    pass


class xcard:
    agent = 'by.mtbank.multicard/1.7 (Noname/Google Nexus 7; Android 22)'

    debug = False  # print each request/reply to stdout

    url = 'https://multicard.mtbank.by:44355/v1/'
    sess = None  # requests.session
    userid = None  # userId

    def __getstate__(self):
        return self.__dict__.copy()

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self):
        self.sess = requests.session()
        self.sess.headers['User-Agent'] = self.agent

    # low-level request interface
    def _request(self, path, payload=None, params=None):
        headers = {}

        if payload is not None:
            headers['Content-Type'] = 'application/json; charset=UTF-8'

        if self.debug:
            if payload is None:
                print('GET: .../%s' % (path,))
            else:
                print('POST: .../%s %s' %
                      (path, json.dumps(payload, indent=4)))

        r = self.sess.request(
            'GET' if payload is None else 'POST',
            self.url + path,
            json=payload,
            params=params,
            headers=headers,
            timeout=(30, 90)
        )

        r.raise_for_status()

        r = r.json()

        if self.debug:
            print('REPLY: %s' % (json.dumps(r, indent=4),))

        if 'code' not in r or not isinstance(r['code'], int):
            raise XCardException('bad reply')

        if r['code'] != 0:
            raise XCardException('Unable to login: %d %s' %
                                 (r['code'], r['message']))

        del r['code']

        return r

    def register(self, pan, cvc2, osid=None, macaddr=None):
        if osid is None:
            chars = '0123456789abcdef'
            osid = ''.join(random.choice(chars) for _ in range(16))

        if macaddr is None:
            octets = ['%02x' % (random.randint(0, 255),) for _ in range(5)]
            macaddr = ':'.join(['00'] + octets)

        chars = string.ascii_letters + string.digits + '_-'
        token = ''.join(random.choice(chars) for _ in range(140))

        r = self._request(
            'register',
            {
                'mobapp': 'MHCE',
                'pan': pan,
                'cvc2': cvc2,
                'token': token,
                'mobInfo': {
                    'device': 'android',
                    'product': 'android',
                    'manufacturer': 'google',
                    'imei': '000000000000000',
                    'model': 'Google Nexus 7',
                    'hceSupport': 'false',
                    'nfcSupport': 'false',
                    'osName': 'ANDROID',
                    'osVersion': '5.1',
                    'osUniqueIdentifier': osid,
                    'macAddress': macaddr
                }
            }
        )

        self.userid = r['userId']

        return r

    def confirmotp(self, otp):
        return self._request(
            'confirmOtp',
            {
                'otp': otp,
                'userId': self.userid,
            }
        )

    def setpassword(self, password):
        return self._request(
            'password',
            {
                'password': password,
                'confirmedPassword': password,
                'userId': self.userid,
            }
        )

    def login(self, userid, password):
        self.userid = userid
        return self._request(
            'login',
            {
                'userId': userid,
                'password': password,
            }
        )

    def mcards(self):
        return self._request(
            'mcards',
            {
                'userId': self.userid
            }
        )
