#!/bin/bash


for i in {1..50}; do
	ip="10.0.0.$((i + 1))"
	echo "Starting node $ip"
	./run.sh "$ip"
done
