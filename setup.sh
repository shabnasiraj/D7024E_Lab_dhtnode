#!/bin/bash

docker build -t dhtnode .
docker network create --subnet=10.0.0.0/16 labnet
