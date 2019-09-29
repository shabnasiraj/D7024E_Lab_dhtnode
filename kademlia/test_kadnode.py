import unittest
from kademlia import kadnode


class NodeTest(unittest.TestCase):

    def setUp(self):
        node = kadnode.KadNode()

    def test_generate_node_id(self):
        for bits in range(1, 10):
            self.assertLess(kadnode.generate_node_id(bits), 2**bits)
