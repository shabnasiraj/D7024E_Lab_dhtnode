
Create the container and docker network:
./setup.sh

Spawn 50 nodes:
./spawn_cluser.sh

Run one instance interactively:
docker run -it --net labnet --ip 10.0.1.1 dhtnode ./node.py -i 10.0.1.1
