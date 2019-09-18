#!/bin/bash

ip=$1

docker run -d --net labnet --ip "$ip" dhtnode ./node.py "$ip"
