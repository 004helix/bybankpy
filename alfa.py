# -*- coding: utf-8 -*-
#
# Alfa-Bank API
#

import lxml.objectify
import requests.utils
import requests
import struct
import json

REALMS = {
	'BY': {
		'ctrl': 'https://click.alfa-bank.by/5mobile/ControllerServlet',
		'gate': 'https://click.alfa-bank.by/5mobile/gate'
	}
}

class GateResult:
	operation = None
	service = None
	header = {}
	fields = []

	def __str__(self):
		data = { 'operationType': '%s:%s' % (self.service, self.operation) }
		if len(self.header) > 0:
			data['header'] = self.header
		if len(self.fields) > 0:
			data['fields'] = self.fields
		return repr(data)
	
	def __repr__(self):
		return str(self)

class alfa:

	os_name       = 'Android'
	os_version    = '22'
	device_name   = 'Android'
	app_version   = '7.2.0'
	lang          = 'ru'
	agent         = 'okhttp/2.6.0'

	sess          = None
	ctrl_url      = None
	gate_url      = None

	sessid        = None

	def __getstate__(self):
		attrs = ['os_name', 'os_version', 'device_name', 'app_version',
		         'lang', 'agent', 'sess', 'ctrl_url', 'gate_url', 'sessid']
		return dict((attr, getattr(self, attr)) for attr in attrs)

	def __setstate__(self, state):
		for name, value in state.items():
			setattr(self, name, value)

	def __init__(self, realm, login = None, passwd = None, sessid = None):

		if realm not in REALMS:
			raise Exception('Unknown realm ' + realm)

		self.ctrl_url = REALMS[realm]['ctrl']
		self.gate_url = REALMS[realm]['gate']

		self.sess = requests.session()
		self.sess.headers['User-Agent'] = self.agent

		if login is not None and passwd is not None:
			params = {
				'appVersion':             self.app_version,
				'deviceName':             self.device_name,
				'login':                  login,
				'loginType':              'password',
				'operationSystem':        self.os_name,
				'operationSystemVersion': self.os_version,
				'password':               passwd
			}

			result = self.gate('Authorization', 'Login', params)

			if 'status' not in result.header or result.header['status'] != 'STATUS_OK':
				raise Exception('Cant login')

			cookies = requests.utils.dict_from_cookiejar(self.sess.cookies)

			if 'JSESSIONID' not in cookies:
				raise Exception('Cant login: JSESSIONID not found')

			self.sessid = cookies['JSESSIONID']

		elif sessid is not None:
			self.sessid = sessid

		else:
			raise Exception('You must set login/passwd pair or session id')

		return

	def _gate(self, service, request):
		url = self.gate_url
		if self.sessid is not None:
			url += ';jsessionid=' + self.sessid

		data = json.dumps(request, ensure_ascii = False).encode('utf-8')

		r = self.sess.post(url,
		                   data = data,
		                   headers = {
		                       'jmb-protocol-version': '1.0',
		                       'jmb-protocol-service': service,
		                       'Content-Type': 'application/octet-stream'
		                   },
		                   timeout = (20, 60)
		)

		return r.json()

	def _ctrl(self, command, *args):
		url = self.ctrl_url
		if self.sessid is not None:
			url += ';jsessionid=' + self.sessid

		req = struct.pack('>B', command)

		if len(args) == 0:
			req += '\x00\x00'
		else:
			for arg in args:
				req += struct.pack('>H', len(arg))
				req += arg

		# login / logout (old)
		if command == 1 or command == 2:
			req += '\x00'

		r = self.sess.post(url,
		                   data = req,
		                   headers = {
		                       'Content-Type': 'application/octet-stream'
		                   },
		                   timeout = (20, 60)
		)

		c = r.content

		# check and parse reply
		if len(c) < 4:
			raise Exception('Reply too small')

		(retval,) = struct.unpack('>I', c[:4])
		c = c[4:]

		if retval != 0:
			(fields_count,) = struct.unpack('>I', c[:4])
			c = c[4:]

			fields = []
			for i in xrange(fields_count):
				(size,) = struct.unpack('>H', c[:2])
				fields.append(str(c[2:size + 2]))
				c = c[2 + size:]

			if len(fields) > 0:
				msg = str(retval) + ': ' + str(fields[0])
			else:
				msg = str(retval) + ': ' + 'Unknown error'

			# logout
			if command == 2:
				return msg
			else:
				raise Exception(msg)

		# login
		if command == 1:
			return c[4:]

		(size,) = struct.unpack('>H', c[:2])

		return str(c[2:2 + size])

	# non-cached
	def summary(self):
		d = lxml.objectify.fromstring(self._ctrl(0x03))

		summary = {
			'accounts': [],
			'credits':  [],
			'deposits': [],
		}

		if len(d.c) > 0:
			for r in d.c[0].r:
				(amount, currency, ) = str(r.f[2]).split()
				summary['accounts'].append({
					'id': r.attrib.get('pk'),
					'description': unicode(r.f[0]),
					'number': str(r.f[1]),
					'amount': amount,
					'currency': currency,
				})

		if len(d.c) > 1:
			for r in d.c[1].r:
				(amount, currency, ) = str(r.f[3]).split()
				summary['credits'].append({
					'id': r.attrib.get('pk'),
					'description': unicode(r.f[0]),
					'number': str(r.f[1]),
					'amount': amount,
					'currency': currency,
					'contract': str(r.f[2]),
				})

		if len(d.c) > 2:
			for r in d.c[2].r:
				(amount, currency, ) = str(r.f[2]).split()
				summary['deposits'].append({
					'id': r.attrib.get('pk'),
					'description': unicode(r.f[0]),
					'number': str(r.f[1]),
					'amount': amount,
					'currency': currency,
				})

		return summary

	def credit_info(self, number):
		request = "<?xml version='1.0' ?>"
		request += '<d><f>%s</f></d>' % str(number)

		info = []

		d = lxml.objectify.fromstring(self._ctrl(0x10, request))

		for f in d.c.r.f:
			info.append({
				'description': unicode(f.attrib.get('t')),
				'value': unicode(f)
			})

		return info

	def transfer(self, fromid, toid, amount, currency):
		form = self._ctrl(0x11)

		request = "<?xml version='1.0' ?>"
		request += '<d o="336"><f1>%s</f1><f4>%s</f4><f2>%s</f2><f3>%s</f3></d>' % \
		           (str(fromid), str(currency), str(toid), str(amount))

		reply = lxml.objectify.fromstring(self._ctrl(0x0d, request))

		op = reply.fs.attrib.get('o')

		f1 = None
		f2 = None
		f4 = None

		for f in reply.fs.f:
			fn = f.attrib.get('n')

			if fn == 'f1':
				f1 = f.v
			elif fn == 'f2':
				f2 = f.v
			elif fn == 'f4':
				f4 = f.v

		request = "<?xml version='1.0' ?>"
		request += '<d o="%s"><f1>%s</f1><f4>%s<f4><f2>%s</f2></d>' % \
		           (str(op), str(f1), str(f4), str(f2))

		return self._ctrl(0x0e, request)

	def gate(self, service, operation, params = {}):
		request = { 'operationId': '%s:%s' % (service, operation) }

		if len(params) > 0:
			request['parameters'] = params

		raw = self._gate(service, request)

		result = GateResult()

		if 'operationId' in raw and raw['operationId'] == 'Exception':
			exc = u'%s: %s' % (raw['header']['faultCode'], raw['header']['faultMessage'])
			raise Exception(exc.encode('utf-8'))

		if 'operationId' in raw:
			(reply_service, reply_operation) = raw['operationId'].split(':')

			if reply_service != service:
				raise Exception('Unknown service %s' % reply_service)

			result.operation = reply_operation

		if 'header' in raw:
			result.header = raw['header']

		if 'fields' in raw:
			result.fields = raw['fields']

		result.service = service

		return result
