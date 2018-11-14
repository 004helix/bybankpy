# -*- coding: utf-8 -*-
#
# Alfa-Bank INSYNC.BY API
#

from __future__ import print_function, unicode_literals
from six.moves import dbm_gnu as gdbm
import six

from datetime import datetime, timedelta
import hashlib
import json


class InsyncHistoryException(Exception):
    pass


class history:
    def __init__(self, client, historydb_filename):
        self.db = gdbm.open(historydb_filename, 'c')
        self.insync = client
        if b'icons' in self.db:
            self.icons = json.loads(self.db['icons'].decode())
        else:
            self.icons = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.db.close()

    def get_amount(self, item):
        if 'operationAmount' in item:
            amount = item['operationAmount']
        else:
            amount = item['info']['amount']

        return ('%.02f' % (amount['amount'],), amount['currency'])

    def get_key(self, item):
        amount = self.get_amount(item)

        md5 = hashlib.md5()
        md5.update(amount[0].encode('utf-8'))  # amount
        md5.update(amount[1].encode('utf-8'))  # currency
        md5.update(item['date'].encode('utf-8'))  # operation date
        md5.update(item['description'].encode('utf-8'))  # merchant
        if 'description' in item['info']:
            md5.update(item['info']['description'].encode('utf-8'))  # account

        return md5.hexdigest()

    def assoc_icon(self, item, transaction_type):
        icon = item['info']['icon']['iconUrl']
        if icon in self.icons:
            if self.icons[icon] != transaction_type:
                if self.icons[icon] != '00':
                    raise InsyncHistoryException(
                        'Icon "%s" already used by transaction type "%s"'
                        % (icon, self.icons[icon])
                    )
                else:
                    self.icons[icon] = transaction_type
                    self.db['icons'] = json.dumps(self.icons)
        else:
            self.icons[icon] = transaction_type
            self.db['icons'] = json.dumps(self.icons)

        return transaction_type

    def get_type(self, item):
        # operation field may be defined
        if 'operation' in item:
            operation = item['operation']

            if operation in ('OWNACCOUNTSTRANSFER',
                             'CREDITCARDTRANSFER',
                             'CREDITTRANSFER',
                             'DEPOSITTRANSFER',
                             'PERSONTRANSFERABB',
                             'COMPANYTRANSFER'):
                return self.assoc_icon(item, 'tr')

            if operation == 'CURRENCYEXCHANGE':
                return self.assoc_icon(item, 'cv')

            if operation == 'PAYMENT':
                return self.assoc_icon(item, 'er')

            raise InsyncHistoryException(
                'Unknown operation "%s"' % (operation, )
            )

        # search using icon cache
        icon = item['info']['icon']['iconUrl']
        if icon in self.icons:
            return self.icons[icon]

        # search online
        if len(item['date']) != 14:
            raise InsyncHistoryException(
                'Malformed item date: %s' % (item['date'],)
            )

        itemdate = datetime(
            int(item['date'][0:4]),    # year
            int(item['date'][4:6]),    # month
            int(item['date'][6:8]),    # day
            int(item['date'][8:10]),   # hour
            int(item['date'][10:12]),  # minute
            int(item['date'][12:14])   # second
        )

        # one month range
        mindate = itemdate.replace(day=1, hour=0, minute=0, second=0)

        if mindate.month == 12:
            maxdate = mindate.replace(year=mindate.year + 1, month=1)
        else:
            maxdate = mindate.replace(month=mindate.month + 1)

        maxdate = maxdate - timedelta(seconds=1)

        # search item using transactionType filters
        for tt in ('cd', 'tr', 'cv', 'at', 'fe', 'ch', 'er'):
            args = {
                'offset': 0,
                'pageSize': 15,
                'maxDate': maxdate.strftime('%Y%m%d%H%M%S'),
                'minDate': mindate.strftime('%Y%m%d%H%M%S'),
                'transactionType': tt
            }

            while True:
                hist = self.insync.history(**args)

                for i in hist['items']:
                    if self.get_key(i) == self.get_key(item):
                        return self.assoc_icon(item, tt)

                if hist['totalItems'] <= args['offset'] + len(hist['items']):
                    break

                args['offset'] += args['pageSize']

        # search without transactionType filter
        args = {
            'offset': 0,
            'pageSize': 15,
            'maxDate': maxdate.strftime('%Y%m%d%H%M%S'),
            'minDate': mindate.strftime('%Y%m%d%H%M%S'),
        }

        while True:
            hist = self.insync.history(**args)

            for i in hist['items']:
                if self.get_key(i) == self.get_key(item):
                    # really unknown transaction type
                    return self.assoc_icon(item, '00')

            if hist['totalItems'] <= args['offset'] + len(hist['items']):
                break

            args['offset'] += args['pageSize']

        raise InsyncHistoryException('Cant find item')

    def reload(self):
        for key in self.db.keys():
            del self.db[key]
        self.db.reorganize()
        self.db.sync()

        self.icons = {}

        args = {
            'offset': 0,
            'pageSize': 15
        }

        while True:
            hist = self.insync.history(**args)
            args['minAmount'] = hist['minAmount']
            args['maxAmount'] = hist['maxAmount']
            args['offset'] += args['pageSize']

            if len(hist['items']) == 0:
                break

            for item in hist['items']:
                self.save(item)

        return

    def save(self, item):
        self.db[self.get_key(item)] = json.dumps(item)

    def pull(self):
        items = list()
        args = {
            'offset': 0,
            'pageSize': 15,
            'shortcutId': "",
        }

        stop = False
        while not stop:
            hist = self.insync.history(**args)

            for item in hist['items']:
                if six.b(self.get_key(item)) in self.db:
                    stop = True
                    break
                items.append(item)

            if hist['totalItems'] <= args['offset'] + len(hist['items']):
                break

            args['offset'] += args['pageSize']

        return list(reversed(items))

    def __iter__(self):
        self.__key = self.db.firstkey()
        if self.__key is not None:
            yield json.loads(self.db[self.__key].decode())
            while self.__key is not None:
                if self.__key == b'icons':
                    self.__key = self.db.nextkey(self.__key)
                    continue
                data = json.loads(self.db[self.__key].decode())
                self.__key = self.db.nextkey(self.__key)
                yield data
