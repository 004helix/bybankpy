# -*- coding: utf-8 -*-
#
# Alfa-Bank INSYNC.BY API
#

from __future__ import print_function, unicode_literals
from six.moves import dbm_gnu as gdbm
import six

from datetime import datetime
import requests
import pickle
import json


class InsyncException(Exception):
    pass


class client:
    lang = 'en'
    devname = 'Android (insync.by py api)'
    appname = 'Android/3.2.3'
    agent = 'okhttp/3.8.1'

    debug = False  # print each request/reply to stdout

    url = 'https://insync.alfa-bank.by/mBank512/v8/'
    sess = None    # requests.session
    sessid = None  # X-Session-ID header
    devid = None   # device id (uuid)

    def __getstate__(self):
        if self.db is not None:
            raise pickle.PicklingError(
                'You have to run login() first to make this object pickable')
        d = self.__dict__.copy()
        del d['db']
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.db = None

    def __init__(self, insyncdb_filename):
        self.db = gdbm.open(insyncdb_filename, 'w')
        self.sess = requests.session()
        self.sess.headers['User-Agent'] = self.agent
        self.sess.headers['X-Client-App'] = self.appname
        self.devid = self.db['uuid'].decode()

    # low-level request interface
    def request(self, path, payload=None, params=None):
        headers = {}

        if payload is not None:
            headers['Content-Type'] = 'application/json; charset=UTF-8'

        if self.sessid is not None:
            headers['X-Session-ID'] = self.sessid

        if self.debug:
            if payload is None:
                print('REQUEST: .../%s' % (path,))
            else:
                print('REQUEST: .../%s %s' %
                      (path, json.dumps(payload, indent=4)))

        r = self.sess.request(
            'GET' if payload is None else 'POST',
            self.url + path,
            json=payload,
            params=params,
            headers=headers,
            timeout=(30, 90)
        )

        if r.status_code >= 400:
            reason = ''
            errmsg = ''

            try:
                reply = json.loads(r.text)
                reason = reply['message']
            except:
                pass

            if reason:
                if 400 <= r.status_code < 500:
                    errmsg = '%s Client Error: %s' % (r.status_code, reason)

                elif 500 <= r.status_code < 600:
                    errmsg = '%s Server Error: %s' % (r.status_code, reason)

            if errmsg:
                if six.PY2:
                    errmsg = errmsg.encode('utf-8')

                raise requests.HTTPError(errmsg, response=r)

        r.raise_for_status()

        if self.debug:
            print('REPLY: %s' % (json.dumps(r.json(), indent=4),))

        return r.json()

    # check device status
    def check_device_status(self):
        reply = self.request(
            'CheckDeviceStatus',
            {
                'deviceId': self.devid,
                'locale': self.lang
            },
            {
                'lang': self.lang
            }
        )

        if 'status' not in reply or \
           not isinstance(reply['status'], six.string_types):
            raise InsyncException('Cant check device status')

        return reply

    # login interface
    def login(self):
        # check device status (retrieve session id)
        self.sessid = None
        device = self.check_device_status()

        if device['status'] != 'ACTIVE':
            raise InsyncException('Device not active: %s', (device['status'],))

        self.sessid = device['sessionId']

        # perform login
        reply = self.request(
            'LoginByToken',
            {
                'deviceId':  self.devid,
                'token':     self.db['token'].decode(),
                'tokenType': 'PIN'
            }
        )

        if 'status' not in reply or \
           not isinstance(reply['status'], six.string_types):
            raise InsyncException('Cant login: bad reply')

        if reply['status'] == 'TOKEN_EXPIRED':
            self.db['token'] = reply['token']
            return self.login()

        if reply['status'] != 'OK':
            raise InsyncException('Cant login: %s', (reply['status'],))

        self.db.close()
        self.db = None

    # def logout interface
    def logout(self):
        return self.request('Logout')

    # auth interface
    def auth(self, **kwargs):
        request = {
            # required fiels in options (resident)
            'isResident':   True,
            #'login':       '',
            #'documentNum': '',
            #'issueDate':   '',
            # auto fields
            'deviceId':     self.devid,
            'deviceName':   self.devname,
            'screenHeight': 1200,
            'screenWidth':  768
        }

        request.update(kwargs)

        reply = self.request(
            'Authorization',
            request,
            {
                'lang': self.lang
            }
        )

        if 'status' not in reply or \
           not isinstance(reply['status'], six.string_types):
            raise InsyncException('Cant auth: bad reply')

        if reply['status'] != 'OK':
            raise InsyncException('Cant auth: %s' % (reply['status'],))

    # auth confirm interface
    def auth_confirm(self, otp):
        reply = self.request(
            'AuthorizationConfirm',
            {
                'deviceId': self.devid,
                'tokenType': 'PIN',
                'otp': otp
            },
            {
                'lang': self.lang
            }
        )

        if 'status' not in reply or \
           not isinstance(reply['status'], six.string_types):
            raise InsyncException('Cant confirm auth: bad reply')

        if reply['status'] != 'OK':
            raise InsyncException('Cant confirm auth: %s' % (reply['status'],))

        self.sessid = reply['sessionId']
        self.db['token'] = reply['token']
        self.db.sync()

    def desktop(self):
        return self.request('Desktop', {'deviceId': self.devid})

    def history(self, **kwargs):
        '''
          Optional request arguments:
            maxAmount: int,
            minAmount: int,
            maxDate: string (20170422134511)
            minDate: string (20150422134511)
            transactionType: string
              cd - Terminal operations
              tr - Transfers
              cv - Currency exchange
              at - ATM cash withdrawals
              fe - Bank fee
              ch - Cash desk operations
              er - SSIS payments
        '''
        args = {
            'offset': 0,
            'pageSize': 15,
            'searchQuery': ''
        }
        args.update(kwargs)
        return self.request('History', args)

    def products(self, product):
        return self.request('Products', {'type': product})

    def account_info(self, accountid, source='SIDEMENU'):
        return self.request('Account/Info', {
            'id': accountid,
            'operationSource': source
        })

    def deposit_info(self, depositid, source='SIDEMENU'):
        return self.request('Deposit/Info', {
            'id': depositid,
            'operationSource': source
        })

    def debit_card_info(self, debitcardid, source='SIDEMENU'):
        return self.request('DebitCard/Info', {
            'id': debitcardid,
            'operationSource': source
        })

    def credit_card_info(self, creditcardid, source='SIDEMENU'):
        return self.request('CreditCard/Info', {
            'id': creditcardid,
            'operationSource': source
        })

    # performance logging
    # rq: DESKTOP_LOAD
    #     START_TO_PROMPT
    # ts: time in milliseconds
    def log(self, rq=None, ts=0):
        return self.request('Log', {
            'deviceId': self.devid,
            'rq': rq,
            'ts': ts
        })

    # desktop shortcuts methods
    def add_product_shortcut(self, type_, id_):
        return self.request('AddProductShortcut', {
            'type': type_,
            'id': id_
        })

    def del_product_shortcut(self, type_, id_):
        return self.request('RemoveProductShortcut', {
            'type': type_,
            'id': id_
        })

    def del_shortcut(self, id_):
        return self.request('DesktopDelete', {
            'shortcutId': id_
        })

    # shortcut ids
    def transfer(self, srcid, dstid, amount, source='DESKTOP'):
        form = self.request('OwnTransfer/Form', {
            'sourceId': str(srcid),
            'destinationId': str(dstid),
            'operationSource': source
        })

        if 'transactionId' not in form:
            raise InsyncException('Bad form: transactionId not found')

        data = self.request('OwnTransfer/Data', {
            'transactionId': form['transactionId'],
            'amount': amount
        })

        if 'status' not in data or \
           not isinstance(data['status'], six.string_types):
            raise InsyncException('Cant transfer: bad data reply')

        if data['status'] != 'OK':
            raise InsyncException('Cant transfer: %s' % (data['status'],))

        return

    def fxrates(self, currency='BYN', date=None):
        if date is None:
            date = datetime.utcnow().strftime('%Y%m%d%H%M%S')

        return self.request('FXRates', {
            'currency': currency,
            'date': date
        })

    # schedules
    def schedules_accounts(self):
        return self.request('Schedules/Accounts')

    def schedules_plans(self):
        return self.request('Schedules/Plans')

    def summary(self):
        accounts = set()
        summary = {
            'accounts': [],
            'deposits': [],
            'loans': []
        }

        for account in self.products('ACCOUNT')['items']:
            accounts.add(account['info']['description'])
            summary['accounts'].append({
                'id': account['id'],
                'title': account['info']['title'],
                'number': account['info']['description'],
                'description': account['info']['description'],
                'currency': account['info']['amount']['currency'],
                'amount': account['info']['amount']['amount']
            })

        for deposit in self.products('DEPOSIT')['items']:
            info = self.deposit_info(deposit['id'])
            due = info['dueDate']
            summary['deposits'].append({
                'id': deposit['id'],
                'title': deposit['info']['title'],
                'number': deposit['info']['description'],
                'description': info['productName'].strip(),
                'currency': deposit['info']['amount']['currency'],
                'amount': deposit['info']['amount']['amount'],
                'rate': info['rate'],
                'due': '%s-%s-%s' % (due[0:4], due[4:6], due[6:8])
            })

        for loan in self.products('LOAN')['items']:
            if loan['type'] == 'CREDITCARD':
                info = self.credit_card_info(loan['id'])

                if info['accountNumber'] not in accounts:
                    try:
                        account = self.account_info(info['objectId'])
                        summary['accounts'].append({
                            'id': account['objectId'],
                            'title': account['info']['title'],
                            'number': account['info']['description'],
                            'description': account['info']['description'],
                            'currency': account['info']['amount']['currency'],
                            'amount': account['info']['amount']['amount']
                        })
                        accounts.add(account['info']['description'])
                    except:
                        pass

            # TODO: loans ?

        return summary