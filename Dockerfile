FROM python:3.7-slim-buster

COPY kademlia kademlia

CMD python3 -m kademlia
