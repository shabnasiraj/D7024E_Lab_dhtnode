import unittest
from kademlia.node_list import NodeList

class NodeListTest(unittest.TestCase):
    ID_SIZE = 8

    def setUp(self):
        self.nl = NodeList(0, self.ID_SIZE, k=3)

    def test_dist_bucket(self):
        testvals = [(0, 0), (1, 0), (2, 1), (63, 5), (64, 6), (2 ** self.ID_SIZE - 1, self.ID_SIZE - 1)]
        for distance, expect_bucket in testvals:
            self.assertEqual(self.nl.distance_to_bucket_index(distance), expect_bucket)

    def test_all_distances(self):
        for distance in range(1, 2 ** self.ID_SIZE):
            bucket_index = self.nl.distance_to_bucket_index(distance)
            self.assertGreaterEqual(distance, 2 ** bucket_index)
            self.assertLessEqual(distance, 2 ** (bucket_index + 1))

    def test_all_duplicate_node(self):
        self.nl.add_node('1.1.1.1', 42, 1)
        self.assertEqual(len(self.nl), 1)

        # Add a node with the same ID again
        self.nl.add_node('2.2.2.2', 2, 1)
        self.assertEqual(len(self.nl), 1)

    def test_add_close(self):
        # We're node ID 0. Node 1 is the closest possible neighbor,
        # it should end up in the first bucket
        self.nl.add_node('1.1.1.1', 42, 1)
        (nodeinfo, _timestamp) = self.nl.bucket_list[0][0]
        self.assertEqual(nodeinfo[2], 1)

    def test_add_distant(self):
        # The most distant node is the inverse of our node ID,
        # it should be put in the last bucket
        distant_node_id = (2 ** self.ID_SIZE) - 1
        self.nl.add_node('2.2.2.2', 999, distant_node_id)
        (nodeinfo, _timestamp) = self.nl.bucket_list[-1][0]
        self.assertEqual(nodeinfo[2], distant_node_id)

    def test_find_closest_empty_list(self):
        # Looking for a node when all buckets are empty should be
        # well-behaved, but return None, no matter where we start.
        self.assertEqual(self.nl.get_k_closest(0), [])
        self.assertEqual(self.nl.get_k_closest(128), [])
        self.assertEqual(self.nl.get_k_closest((2 ** self.ID_SIZE) - 1), [])

    def test_find_closest_one(self):
        # If there's a single node in the list, it's closest to everything
        self.nl.add_node('1.1.1.1', 42, 1)
        for nodeid in range(2 ** self.ID_SIZE):
            node = self.nl.get_k_closest(nodeid)[0]
            self.assertEqual(node[2], 1)

    def test_find_closest_node_idempotent(self):
        self.nl.add_node('2.2.2.2', 123, 1)
        self.nl.add_node('2.2.2.2', 123, 100)
        self.assertEqual(self.nl.get_closest_node(2), self.nl.get_closest_node(2))

    def test_offset_pattern(self):
        self.assertEqual(list(NodeList.zig_zag_offsets(5)), [0, -1, 1, -2, 2])

    def test_length(self):
        self.assertEqual(len(self.nl), 0)
        self.nl.add_node('1.1.1.1', 42, 1)
        self.assertEqual(len(self.nl), 1)

        for x in range(1, self.ID_SIZE):
            self.nl.add_node('1.2.3.4', 1, 2**x)
            self.nl.add_node('5.6.7.8', 1, 2**x + 1)

        self.assertEqual(len(self.nl), 2*(self.ID_SIZE - 1) + 1)

    def test_get_node_info(self):
        testnodes = [('1.1.1.1', 100, 1),
                     ('2.2.2.2', 101, 2),
                     ('3.3.3.3', 102, 3),
                     ('4.4.4.4', 103, 4),
                     ('5.5.5.5', 104, 2**self.ID_SIZE - 1)]
        for node in testnodes:
            self.nl.add_node(node[0], node[1], node[2])

        for node in testnodes:
            (ip, port, nodeid) = self.nl.get_node_info(node[2])
            self.assertEqual(ip, node[0])
            self.assertEqual(port, node[1])
            self.assertEqual(nodeid, node[2])

        # Look for a node that shoudn't exist
        node = self.nl.get_node_info(55)
        self.assertIsNone(node)

    def test_sorted_nodelist(self):
        nodelist = [
            ('', 0, 0x0),
            ('', 0, 0xff),
            ('', 0, 0x55),
            ('', 0, 0x1)
        ]
        expected = [
            ('', 0, 255),
            ('', 0, 0),
            ('', 0, 1),
            ('', 0, 85)
        ]
        self.assertEqual(self.nl.sort_by_distance(nodelist, 128), expected)
