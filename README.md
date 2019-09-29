
# Build container:
docker build -t kadnode .

# Deploy swarm:
docker stack deploy --compose-file docker-compose.yml kad

# Stop swarm:
docker stack down kad

# View node output:
docker service logs --raw -f kad_kademlia

# Run unit tests:
python3 -m nose2 -v --with-coverage

# Attach to the CLI of a running container
* Run "docker ps" to list container, find an ID and run "docker attach <ID>"
* To detach, press ctrl+p ctrl+q


# Known limitations

*