#!/usr/bin/python

import alfa
import json

a = alfa.alfa('BY', 'login', 'password')

# transfer between account example
#a.transfer('30140000000010270', '30140000000020270', '1.00', 'USD')

# accounts / credits / deposits summary example
summary = a.summary()

print json.dumps(summary, indent = 4)
