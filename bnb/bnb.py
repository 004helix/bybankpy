# -*- coding: utf-8 -*-
#
# BNB API
#

import lxml.etree
import lxml.builder
import lxml.objectify
import datetime
import requests


class client:
    gate_url = 'https://bs.imbanking.by/mobile/xml_online'
    terminal = 'Android'
    appver = '1.3.4'

    sessid = None
    sess = None

    E = None

    def __getstate__(self):
        attrs = ['gate_url', 'terminal', 'appver', 'sessid', 'sess']
        return dict((attr, getattr(self, attr)) for attr in attrs)

    def __setstate__(self, state):
        self.E = lxml.builder.ElementMaker()
        for name, value in state.items():
            setattr(self, name, value)

    def __init__(self, login=None, passwd=None, sessid=None):
        self.E = lxml.builder.ElementMaker()

        self.sess = requests.session()

        if login is not None and passwd is not None:
            reply = self.request(
                'admin',
                [
                    self.E.Login(
                        self.E.Parameter(login, Id='Login'),
                        self.E.Parameter(passwd, Id='Password'),
                        Type='PWD'
                    ),
                    self.E.RequestType('Login'),
                    self.E.Subsystem('ClientAuth'),
                ]
            )
            self.sessid = str(reply.Login.SID)

        elif sessid is not None:
            self.sessid = sessid

        else:
            raise Exception('You must set login/passwd pair or session id')

    def request(self, ext, fields=[]):
        root = getattr(self.E, 'BS_Request')
        tid = getattr(self.E, 'TerminalId')
        tt = getattr(self.E, 'TerminalTime')

        xml = root(
            tid(self.terminal, AppVersion=self.appver),
            tt(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        )

        for field in fields:
            xml.append(field)

        reply = self.sess.post(
            self.gate_url + '.' + ext,
            data={
                'XML': lxml.etree.tostring(xml, pretty_print=True).strip()
            },
            timeout=(20, 60))

        reply.raise_for_status()
        reply = lxml.objectify.fromstring(reply.content)

        errcnt = 0
        errtxt = u'<unknown>'

        try:
            errcnt = int(reply.Error.attrib.get('Count'))
            errtxt = u' '.join(map(unicode, reply.Error.ErrorLine))
        except:
            pass

        if errcnt > 0:
            errtxt = str(errcnt) + ': ' + errtxt
            raise Exception(errtxt.encode('utf-8'))

        return reply

    def get_products(self):
        reply = self.request(
            'admin',
            [
                self.E.GetProducts(ProductType='PAY_TOOL', GetActions='N'),
                self.E.RequestType('GetProducts'),
                self.E.Session(SID=self.sessid),
                self.E.Subsystem('ClientAuth')
            ]
        )

        prods = []

        for p in reply.GetProducts.Product:
            r = {}
            for name in p.attrib:
                r[name] = unicode(p.attrib.get(name))
            prods.append(r)

        return prods

    def get_client_info(self):
        reply = self.request(
            'admin',
            [
                self.E.GetClientInfo(''),
                self.E.RequestType('GetClientInfo'),
                self.E.Session(SID=self.sessid),
                self.E.Subsystem('ClientAuth')
            ]
        )

        info = {}

        for field in reply.GetClientInfo.iter():
            if field.tag == 'GetClientInfo':
                continue
            info[field.tag] = unicode(field.text)

        return info

    def get_balance(self, clientid, product={}):
        if 'ProductType' not in product or product['ProductType'] != 'MS':
            raise Exception('Usupported product type')

        reply = self.request(
            'request',
            [
                self.E.AuthClientId(product['No'], IdType='MS'),
                self.E.Balance(Currency=product['Currency']),
                self.E.ClientId(clientid, IdType='Client'),
                self.E.RequestType('Balance'),
                self.E.Session(SID=self.sessid),
                self.E.TerminalCapabilities(
                    self.E.AnyAmount('Y'),
                    self.E.ScreenWidth('62'),
                    self.E.BooleanParameter('Y'),
                    self.E.LongParameter('Y')
                )
            ]
        )

        balance = str(reply.Balance.Amount.text)
        return float(balance.replace(',', '.'))
