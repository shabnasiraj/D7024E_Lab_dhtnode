import socket
import threading
import hashlib

import random
import time
import logging
import sys

from kademlia import node_list
from kademlia import protocol

PORT = 1337
ALPHA = 3

def generate_node_id(size):
    return random.getrandbits(size)

class KadNode(object):
    def __init__(self, listenip=None, node_id=None):
        self.id_size = 160
        self.listenip = listenip
        self.node_id = node_id or generate_node_id(self.id_size)
        self.logger = self.setup_logger()
        self.node_list = node_list.NodeList(id_size=self.id_size, nodeid=self.node_id)
        self._stop_recv = False
        self._recv_thread = None
        self.stored_data = {}

        self.logger.info(f'Initialized node {self.node_id}')

    def __str__(self):
        return f'Node {self.node_id}'

    def ping_node(self, nodeid):
        (addr, port, _nodeid) = self.node_list.get_node_info(nodeid)
        self.ping_ip(addr, port)

    def send_find_node(self, nodeid, peer_ip, peer_port, find_value=False):
        if find_value:
            findmsg = protocol.RPCMessage.find_value_request(sender=self.node_id, key=nodeid)
        else:
            findmsg = protocol.RPCMessage.find_node_request(sender=self.node_id, nodeid=nodeid)
        sock = self.send(peer_ip, peer_port, str(findmsg))
        resp = self.wait_for_response(sock)

        if not resp:
            self.logger.warning('FIND_NODE timeout')
            return None

        self.logger.debug('Got response: %s', resp)
        respmsg = protocol.RPCMessage.parse(resp)
        if respmsg.rpcid != findmsg.rpcid:
            self.logger.error('Invalid RPC ID in FIND_NODE response')

        self.logger.debug('FIND_NODE response from node %s: %s', respmsg.sender, respmsg.data)

        return respmsg.data


    def node_lookup(self, nodeid, find_value=False):

        closest = self.node_list.get_n_closest(nodeid, ALPHA)
        shortlist = node_list.NodeList.sort_by_distance(closest, nodeid)

        if not shortlist:
            self.logger.warning('Failed to find node for FIND_NODE request')
            return None

        contacted = []
        closest_node = closest[0]

        while True:
            found_nodes = []
            for sendto in shortlist:

                (sendtoip, sendtoport, nid) = sendto

                if nid in contacted:
                    continue
                contacted.append(nid)

                ret = self.send_find_node(nodeid, sendtoip, sendtoport, find_value)
                if find_value and 'value' in ret:
                    return ret['value']
                else:
                    new_nodes = ret['nodes']

                if not new_nodes:
                    # TODO: Failed to respond - remove from shortlist
                    continue

                for ip, port, nid in new_nodes:
                    self.node_list.add_node(ip, port, nid)

                for node in new_nodes:
                    if not node_list.NodeList.node_in_list(found_nodes, node):
                        found_nodes.append(node)

            for node in found_nodes:
                if not node_list.NodeList.node_in_list(shortlist, node):
                    shortlist.append(node)
            shortlist = node_list.NodeList.sort_by_distance(shortlist, nodeid)
            new_closest = shortlist[0]

            # The sequence of parallel searches is continued until either no
            # node in the sets returned is closer than the closest node already
            # seen or the initiating node has accumulated k probed and known
            # to be active contacts.
            if node_list.distance(closest_node[2], nodeid) <= node_list.distance(new_closest[2], nodeid):
                return shortlist[:self.node_list.k]

            closest_node = new_closest
        return shortlist[:self.node_list.k]


    def store_value(self, value):
        sha1 = hashlib.sha1(value.encode())
        key = int(sha1.hexdigest(), 16)

        # Truncate the key to the node ID size.
        # Only really needed when using shorter IDs for debugging,
        # but it never hurts.
        key &= (2**self.id_size) - 1
        nodes = self.node_lookup(key)
        if not nodes:
            return None
        self.logger.debug('Node lookup returned %s for key %s', nodes, key)

        storemsg = protocol.RPCMessage.store_request(self.node_id, key, value)

        success = 0
        for (addr, port, nodeid) in nodes:
            self.logger.debug('Storing key %s on node %s', key, nodeid)
            sock = self.send(addr, port, str(storemsg))
            resp = self.wait_for_response(sock)

            if not resp:
                self.logger.warning('Timeout waiting for STORE response')
                continue

            respmsg = protocol.RPCMessage.parse(resp)
            if respmsg.rpcid != storemsg.rpcid:
                self.logger.error('Invalid RPC ID in STORE response')
                continue

            if respmsg.data['result']:
                success += 1

        return (key, success)

    def get_value(self, key):
        key &= (2**self.id_size) - 1
        return self.node_lookup(key, find_value=True)


    def ping_ip(self, addr, port):
        pingmsg = protocol.RPCMessage.ping_request(sender=self.node_id)
        try:
            sock = self.send(addr, port, str(pingmsg))
        except socket.gaierror:
            # DNS error
            return None

        resp = self.wait_for_response(sock)
        if not resp:
            self.logger.warning('ping timeout')
            return None

        self.logger.debug('Got response: %s', resp)
        respmsg = protocol.RPCMessage.parse(resp)
        if respmsg.rpcid != pingmsg.rpcid:
            self.logger.error('Invalid RPC ID in PING response')
            return None

        self.logger.debug('PING response from node %s', respmsg.sender)
        self.node_list.add_node(addr, PORT, respmsg.sender)
        return respmsg.sender

    def setup_logger(self):
        root = logging.getLogger('kademlia')
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(hex(self.node_id) + ': %(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        return root

    def start_receive(self):
        thread = threading.Thread(target=self._receive)
        thread.daemon = True
        thread.start()
        self._recv_thread = thread

    def _receive(self):
        thishost = socket.getfqdn()
        self.listenip = self.listenip or socket.gethostbyname(thishost)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sock.bind((self.listenip, PORT))
        self.logger.info('Listening on %s:%s (%s)', thishost, PORT, self.listenip)

        while not self._stop_recv:
            try:
                (msg, addr) = sock.recvfrom(protocol.MAX_MSG_SIZE)
            except socket.timeout:
                continue
            msg = msg.decode()
            self.logger.debug('message from %s: %s', addr, msg)

            resp = self.handle_request(msg, addr[0])
            if resp:
                sock.sendto(str(resp).encode(), addr)
        self.logger.info('Stopping receive thread')

    def _handle_ping_request(self, rpc, sender_ip):
        self.logger.debug('Ping from node %s @ %s', rpc.sender, sender_ip)
        self.node_list.add_node(sender_ip, PORT, rpc.sender)
        return protocol.RPCMessage.ping_response(self.node_id, rpc.rpcid)

    def _handle_find_node_request(self, rpc, sender_ip):
        find_node = rpc.data['nodeid']
        self.logger.debug('FIND_NODE request for %s', find_node)
        self.node_list.add_node(sender_ip, PORT, rpc.sender)

        if find_node == self.node_id:
            self.logger.warning('FIND_NODE request issued with with own node ID. Weird, but ok?')

        return_nodes = self.node_list.get_k_closest(find_node)
        return protocol.RPCMessage.find_node_response(self.node_id, return_nodes, rpc.rpcid)

    def _handle_store_request(self, rpc, sender_ip):
        args = rpc.data
        result = True
        if 'key' not in args or 'value' not in args:
            self.logger.warning('Invalid arguments in STORE message: %s', args)
            result = False

        self.logger.debug('Storing local data, key: %s, value: %s', args['key'], args['value'])
        self.stored_data[args['key']] = args['value']
        return protocol.RPCMessage.store_response(self.node_id, result=result, rpcid=rpc.rpcid)

    def _handle_find_value_request(self, rpc, sender_ip):
        key = rpc.data['key']

        if key in self.stored_data:
            return_value = self.stored_data[key]
            return protocol.RPCMessage.find_value_response(self.node_id, rpcid=rpc.rpcid, result=return_value, found_val=True)
        else:
            return_nodes = self.node_list.get_k_closest(key)
            return protocol.RPCMessage.find_value_response(self.node_id, rpcid=rpc.rpcid, result=return_nodes, found_val=False)


    def handle_request(self, msg, sender_ip):
        rpc = protocol.RPCMessage.parse(msg)

        if rpc.msgtype != 'req':
            self.logger.warning('Unexpected message type recieved')
            return None

        if rpc.command == protocol.RPCCommand.PING:
            return self._handle_ping_request(rpc, sender_ip)
        elif rpc.command == protocol.RPCCommand.FIND_NODE:
            return self._handle_find_node_request(rpc, sender_ip)
        elif rpc.command == protocol.RPCCommand.STORE:
            return self._handle_store_request(rpc, sender_ip)
        elif rpc.command == protocol.RPCCommand.FIND_VALUE:
            return self._handle_find_value_request(rpc, sender_ip)
        else:
            self.logger.error('Unknown RPC command: %s', rpc.command)
            return None

    def send(self, addr, port, msg):
        self.logger.debug('Sending %s to %s', msg, addr)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(msg.encode(), (addr, port))
        return sock

    @staticmethod
    def wait_for_response(sock, timeout=2):
        sock.settimeout(timeout)
        try:
            (resp, _) = sock.recvfrom(protocol.MAX_MSG_SIZE)
            return resp.decode()
        except socket.timeout:
            return None

    def join_network(self, join_ip):
        self.logger.info('Joining network from seed node %s', join_ip)
        while True:
            seed_node_id = self.ping_ip(join_ip, PORT)
            if seed_node_id:
                self.logger.info('Joined network!')
                break
            else:
                self.logger.warning('Failed to join network. Retrying in 1 second')
                time.sleep(1)

    def close(self):
        self._stop_recv = True
        self._recv_thread.join()