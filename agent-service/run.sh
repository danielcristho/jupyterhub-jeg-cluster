docker run --name agent -d \
    --net=host \
    -e DISCOVERY_URL=http://192.168.122.1:15002/register-node \ 
    danielcristh0/agent:1.1

docker run --name agent -d \
    --net=host \
    -e DISCOVERY_URL=http://10.21.73.116:15002/register-node \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --gpus all \
    danielcristh0/agent:1.1
