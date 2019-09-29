import unittest
from kademlia import protocol

class ProtocolTest(unittest.TestCase):

    def test_ping_msg(self):
        ping_msg = protocol.RPCMessage.ping_request(123)
        ping_str = str(ping_msg)
        parsed = protocol.RPCMessage.parse(ping_str)

        self.assertEqual(ping_msg.msgtype, parsed.msgtype)
        self.assertEqual(ping_msg.command, parsed.command)
        self.assertEqual(ping_msg.sender, parsed.sender)
        self.assertEqual(ping_msg.rpcid, parsed.rpcid)

    def test_find_node_response_size(self):
        id_size = 160
        k = 20
        nodes = k * [('111.111.111.111', 22222, 2**id_size)]
        resp = protocol.RPCMessage.find_node_response(2**id_size, nodes, 2**160)
        self.assertLessEqual(len(str(resp)), protocol.MAX_MSG_SIZE)
