FROM python:3.7-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

RUN git clone https://github.com/SKAJohanVenter/katcp_prometheus_bridge /app/katcp_prometheus_bridge
RUN ls -l 
RUN ls -l /app
RUN python /app/katcp_prometheus_bridge/setup.py install
EXPOSE 8080
CMD [ ! -z "${KATCP_HOST}" ] || { echo "KATCP_HOST cannot be empty, pass in as env variable"; exit 1; } && \
    [ ! -z "${KATCP_PORT}" ] || { echo "KATCP_PORT cannot be empty, pass in as env variable"; exit 1; } && \
    python -u /app/katcp_prometheus_bridge/katcp_prometheus_bridge/bridge.py

