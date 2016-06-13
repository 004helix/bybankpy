# -*- coding: utf-8 -*-

# http://www.currency-iso.org/dam/downloads/lists/list_one.xml
# https://www.nbrb.by/Legislation/documents/p_33-20-44.pdf

ISO4217 = {
	'974': 'BYR',
	'933': 'BYN',
	'840': 'USD',
	'978': 'EUR',
	'643': 'RUB',
}

def num2name(num):
	if str(num) in ISO4217:
		return ISO4217[str(num)]
	return '?'

def name2num(name):
	inv = { v: k for k, v in ISO4217.items() }
	if name in inv:
		return int(env[name])
	return 0
