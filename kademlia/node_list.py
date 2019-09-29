import math
import datetime
import logging
import itertools

def distance(id1, id2):
    return id1 ^ id2

class NodeList(object):
    def __init__(self, nodeid, id_size, k=20):

        self.logger = logging.getLogger('kademlia')
        self.nodeid = nodeid
        self.id_size = id_size
        self.bucket_list = []
        self.k = k
        for _ in range(id_size):
            self.bucket_list.append([])

    def __len__(self):
        return sum([len(bucket) for bucket in self.bucket_list])

    @staticmethod
    def distance_to_bucket_index(dist):
        if dist == 0:
            return 0

        return int(math.log(dist, 2))

    def get_bucket_index(self, otherid):
        dist = distance(self.nodeid, otherid)
        return self.distance_to_bucket_index(dist)

    def add_node(self, ip, port, nodeid):
        bucket = self.bucket_list[self.get_bucket_index(nodeid)]

        ts = datetime.datetime.now().timestamp()
        if len(bucket) < self.k:
            if not self.bucket_contains_node(bucket, nodeid):
                self.logger.debug('Adding node %s @ %s:%s', nodeid, ip, port)
                bucket.append(((ip, port, nodeid), ts))
                self.logger.debug('Bucket: %s', bucket)
        else:
            # TODO: eviction logic, for now, just ignore
            # the new node if the bucket if full
            pass

    @staticmethod
    def bucket_contains_node(bucket, nodeid):
        for (node, _ts) in bucket:
            if node[2] == nodeid:
                return True
        return False

    @staticmethod
    def zig_zag_offsets(max):
        offset = 0
        for count in range(max):
            sign = -1 if count % 2 else 1
            offset += sign * count
            yield offset

    def close_nodes(self, nodeid):
        start_index = self.get_bucket_index(nodeid)

        # Look for a node in the expected bucket.
        # If that's empty, move check bucket at offset -1, +1, -2, +2, -3 and so on
        # Worst case, we started on the first or last bucket, in which case
        # we need to go through 2 x ID_SIZE iterations.
        for offset in self.zig_zag_offsets(self.id_size * 2):
            bucket_index = start_index + offset

            if bucket_index < 0 or bucket_index >= len(self.bucket_list):
                continue

            bucket = self.bucket_list[bucket_index]
            if bucket:
                # TODO: find the closest node in this bucket,
                # for now, just return them in the order found
                for node in bucket:
                    ret = node[0]
                    yield ret

    def get_n_closest(self, nodeid, n):
        return list(itertools.islice(self.close_nodes(nodeid), n))

    def get_k_closest(self, nodeid):
        return self.get_n_closest(nodeid, self.k)

    def get_closest_node(self, nodeid):
        nodes = list(itertools.islice(self.close_nodes(nodeid), 1))
        return nodes[0] if nodes else None

    def get_node_info(self, nodeid):
        bucket = self.bucket_list[self.get_bucket_index(nodeid)]
        for (node, _timestamp) in bucket:
            (_ip, _port, nid) = node
            if nid == nodeid:
                return node
        return None

    @staticmethod
    def node_in_list(nodelist, node):
        (_new_ip, _new_port, nodeid) = node
        for (_ip, _port, nid) in nodelist:
            if nid == nodeid:
                return True
        return False

    @staticmethod
    def sort_by_distance(nodelist, target_nodeid):
        return sorted(nodelist, key=lambda node: distance(node[2], target_nodeid))
