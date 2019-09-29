#!/usr/bin/env python3
import argparse

from kademlia import kadnode

def run_cli(node):
    def get_prompt():
        col_red = '\033[91m'
        col_end = '\033[0m'
        return col_red + '[{} nodes] '.format((len(node.node_list))) + col_end + '> '

    while True:
        try:
            cmd = input(get_prompt())
        except EOFError:
            break

        if not cmd:
            continue

        split = cmd.split(None, 1)
        cmd = split[0]

        if cmd == 'exit':
            break
        elif cmd == 'put':
            ret = node.store_value(split[1])
            if ret:
                print(f'Stored key: {ret[0]} on {ret[1]} nodes')
            else:
                print('Failed to store data')
        elif cmd == 'get':
            ret = node.get_value(int(split[1]))
            print(f'Value: {ret}')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen-ip')
    parser.add_argument('--join')
    args = parser.parse_args()

    node = kadnode.KadNode(args.listen_ip)
    node.start_receive()

    if args.join:
        node.join_network(args.join)

    try:
        run_cli(node)
    except KeyboardInterrupt:
        print()

    node.close()

if __name__ == '__main__':
    main()
