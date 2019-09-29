import json
import enum
import random

MAX_MSG_SIZE = 2000

class RPCCommand(enum.Enum):
    PING = 1
    STORE = 2
    FIND_NODE = 3
    FIND_VALUE = 4


class RPCMessage(object):
    """
    {
        "msgtype" <req|resp>,
        "rpc": <RPCCommand>,
        "sender": <nodeid>,
        "rpcid": <160 bit unique id>
        "data": {
            <arguments or return data>
        }
    }
    """

    REQ = 'req'
    RESP = 'resp'
    REQUIRED_KEYS = ['msgtype', 'command', 'sender', 'rpcid']

    def __init__(self, msgtype, command, sender, rpcid=None, data=None):
        self.msgtype = msgtype
        self.command = command
        self.sender = sender
        self.rpcid = rpcid or random.getrandbits(160)
        self.data = data

    @classmethod
    def ping_request(cls, sender):
        return cls(cls.REQ, RPCCommand.PING, sender)

    @classmethod
    def ping_response(cls, sender, rpcid):
        return cls(cls.RESP, RPCCommand.PING, sender, rpcid=rpcid)

    @classmethod
    def find_node_request(cls, sender, nodeid):
        args = {'nodeid': nodeid}
        return cls(cls.REQ, RPCCommand.FIND_NODE, sender, data=args)

    @classmethod
    def find_node_response(cls, sender, nodes, rpcid):
        data = {'nodes': nodes}
        return cls(cls.RESP, RPCCommand.FIND_NODE, sender, rpcid=rpcid, data=data)

    @classmethod
    def store_request(cls, sender, key, value):
        args = {'key': key, 'value': value}
        return cls(cls.REQ, RPCCommand.STORE, sender, data=args)

    @classmethod
    def store_response(cls, sender, result, rpcid):
        args = {'result': result}
        return cls(cls.RESP, RPCCommand.STORE, sender, rpcid=rpcid, data=args)

    @classmethod
    def find_value_request(cls, sender, key):
        args = {'key': key}
        return cls(cls.REQ, RPCCommand.FIND_VALUE, sender, data=args)

    @classmethod
    def find_value_response(cls, sender, result, rpcid, found_val):
        if found_val:
            data = {'value': result}
        else:
            data = {'nodes': result}
        return cls(cls.RESP, RPCCommand.FIND_VALUE, sender, rpcid=rpcid, data=data)

    @classmethod
    def parse(cls, msgstr):
        msg = json.loads(msgstr)

        for key in cls.REQUIRED_KEYS:
            if key not in msg:
                raise AttributeError(f'Invalid message. Key "{key}" not found')

        if msg['msgtype'] not in [cls.REQ, cls.RESP]:
            raise AttributeError('Invalid message type: {}'.format(msg['msgtype']))

        return cls(msg['msgtype'],
                   RPCCommand(msg['command']),
                   msg['sender'],
                   rpcid=msg['rpcid'],
                   data=(msg['data'] if 'data' in msg else None))

    def __str__(self):
        msg = {'msgtype': self.msgtype,
               'command': self.command.value,
               'sender': self.sender,
               'rpcid': self.rpcid
              }
        if self.data:
            msg['data'] = self.data

        return json.dumps(msg)
