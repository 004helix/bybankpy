# -*- coding: utf-8 -*-
#
# MMBank ib api
#

from __future__ import print_function, unicode_literals

import requests
import json


class MMBankException(Exception):
    pass


class client:
    agent = 'okhttp/3.9.1'

    debug = False  # print each request/reply to stdout

    url = 'https://ib.mmbank.by/services/v2/'
    sess = None  # requests.session
    sessid = None  # session token
    appid = '1.33'
    browser = 'Android'
    browser_version = 'Google Nexus 7 (Android)'
    platform = 'Android'
    platform_version = '5.1'

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
            headers['Content-Type'] = 'application/json; charset=utf-8'

        if self.sessid is not None:
            headers['session_token'] = self.sessid

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

        if 'errorInfo' in r and 'error' in r['errorInfo']:
            if 0 != int(r['errorInfo']['error']):
                raise MMBankException('error' + r['errorInfo']['errorText'])

        if 'errorInfo' in r:
            del r['errorInfo']

        return r

    def login(self, user, password):
        r = self._request('session/login', {
                'applicID': self.appid,
                'browser': self.browser,
                'browserVersion': self.browser_version,
                'platform': self.platform,
                'platformVersion': self.platform_version,
                'deviceUDID': '0000000000000000',
                'clientKind': '0',
                'pushId': '',
                'login': user,
                'password': password,
        })

        if 'sessionToken' not in r:
            raise MMBankException('sessionToken not found')

        self.sessid = r['sessionToken']

    def getclient(self):
        r = self._request('user/getclient', {})
        return r['user']

    def getaccounts(self):
        r = self._request('products/getUserAccountsOverview', {
            'additionCardAccount': {},
            "cardAccount": {
                "withBalance": "null"
            },
            "corpoCardAccount": {},
            "creditAccount": {},
            "currentAccount": {},
            "depositAccount": {}
        })
        return r['overviewResponse']

    def getbalance(self, cardhash):
        return self._request('card/getBalance', {
            'cardHash': cardhash
        })
