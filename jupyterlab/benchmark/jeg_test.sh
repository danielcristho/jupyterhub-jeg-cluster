export JEG_AUTH_TOKEN="jeg-jeg-an"
export JEG_HOST_IP="10.33.17.30"
export JEG_PORT="8889"

curl -H "Authorization: token $JEG_AUTH_TOKEN" http://$JEG_HOST_IP:$JEG_PORT/api/kernelspecs


curl -X POST -H "Authorization: token jeg-jeg-an" "Content-Type: application/json" -d '{"name": "python3"}' http://10.33.17.30:8889/api/kernels