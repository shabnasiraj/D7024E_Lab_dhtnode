#!/usr/bin/env python3

import socket
import threading
import argparse

PORT = 1337

def handle_req(msg):
    if msg == 'PING':
        return 'PONG'
    return 'UNKNOWN'

def receive(listen_addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    sock.bind((listen_addr, PORT))
    print('Listening on {}:{}'.format(listen_addr, PORT))

    while True:
        (msg, addr) = sock.recvfrom(256)
        cmd = msg.decode()
        print('message from {}: {}'.format(addr, cmd))

        resp = handle_req(cmd)
        sock.sendto(resp.encode(), addr)

def ping(addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto('PING'.encode(), (addr, PORT))
    (resp, _) = sock.recvfrom(256)
    print('Got response: {}'.format(resp.decode()))

def run_prompt():
    while True:
        try:
            cmd = input('# ').split()
        except EOFError:
            break

        if not cmd:
            continue

        if cmd[0] == 'ping':
            if len(cmd) != 2:
                print('USAGE: ping <address>')
                continue
            ping(cmd[1])
        else:
            print('unknown command')

def main(args):
    recv_thread = threading.Thread(target=receive, args=(args.ip,))
    recv_thread.daemon = True
    recv_thread.start()

    if args.interactive:
        run_prompt()
    
    recv_thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ip')
    parser.add_argument('--interactive', '-i', action='store_true', default=False)
    args = parser.parse_args()

    try:
        main(args)
    except KeyboardInterrupt:
        print()
