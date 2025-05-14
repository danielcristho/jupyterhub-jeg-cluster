.PHONY: raycluster

# Ray
kuberay_version = 1.2.2
cluster = kuberay
service = raycluster-$(cluster)-head-svc

# Jupyterhub
jupyterhub_version = 4.0.0

## install kubernetes network plugin
# network-plugin:
# 	kubectl apply -f /home/ray/k3s-ray-jupyterlab/infra/base/manifests/networks/calico.yaml

## install nvidia gpu-operator
gpu-operator:
	helm repo add nvdp https://nvidia.github.io/k8s-device-plugin \
	&& helm repo update
	helm install --generate-name nvdp/nvidia-device-plugin --namespace kube-system
	kubectl get pods -n kube-system|grep -i nvidia

## install kuberay operator using quickstart manifests
kuberay:
# add helm repo and update to latest
	# kubectl label node k3s-worker1 node-role.kubernetes.io/worker=worker
	# kubectl label node k3s-worker2 node-role.kubernetes.io/worker=worker
	helm repo add kuberay https://ray-project.github.io/kuberay-helm/
	helm repo update kuberay
	helm upgrade --install kuberay-operator kuberay/kuberay-operator --version $(kuberay_version) --wait --debug > /dev/null

## create ray cluster
raycluster:
	helm upgrade \
		--install raycluster kuberay/ray-cluster \
		--version $(kuberay_version) \
		--values infra/kubernetes/ray/values.yaml \
		--wait --debug > /dev/null
# restart needed because of https://github.com/ray-project/kuberay/issues/234
	make restart

## restart the ray cluster
restart:
	kubectl delete pod -lapp.kubernetes.io/name=kuberay --wait=false || true

## get shell on head pod
shell:
	kubectl exec -i -t service/$(service) -- /bin/bash

## port forward the service
ray-forward:
	kubectl port-forward svc/$(service) 10001:10001 8265:8265 6379:6379 --address=0.0.0.0

## status
status: $(venv)
	$(venv)/bin/ray status --address 192.168.122.10:6379 -v

## print ray commit
version: $(venv)
	$(venv)/bin/python -c 'import ray; print(f"{ray.__version__} {ray.__commit__}")'

## remove cluster
delete:
	kubectl delete raycluster raycluster-$(cluster)

## ping server endpoint
ping: $(venv)
	$(venv)/bin/python -m raydemo.ping

## head node logs
logs-head:
	kubectl logs -lray.io/cluster=raycluster-kuberay -lray.io/node-type=head -c ray-head -f

## worker node logs
logs-worker:
	kubectl logs -lray.io/group=workergroup -f

## auto-scaler logs
logs-as:
	kubectl logs -lray.io/cluster=raycluster-kuberay -lray.io/node-type=head -c autoscaler -f

## enable trafefik debug loglevel
tdebug:
	kubectl -n kube-system patch deployment traefik --type json -p '[{"op": "add", "path": "/spec/template/spec/containers/0/args/0", "value":"--log.level=DEBUG"}]'

## tail traefik logs
tlogs:
	kubectl -n kube-system logs -l app.kubernetes.io/name=traefik -f

## forward traefik dashboard
tdashboard:
	@echo Forwarding traefik dashboard to http://192.168.122.10:9000/dashboard/
	tpod=$$(kubectl get pod -n kube-system -l app.kubernetes.io/name=traefik -o custom-columns=:metadata.name --no-headers=true) && \
		kubectl -n kube-system port-forward $$tpod 9000:9000

## run tf_mnist on cluster
tf_mnist: $(venv)
	$(venv)/bin/python -m raydemo.tf_mnist --address ray://192.168.122.10:10001

## list jobs
job-list: $(venv)
	$(venv)/bin/ray job list --address http://192.168.122.10:8265

## JupyterHub initialize
jupyterhub-install:
	helm repo add jupyterhub https://hub.jupyter.org/helm-chart
	helm repo update

## Create pvc
jupyterhub-pvc:
	kubectl create namespace jhub --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f /home/daniel/k3s-ray-jupyterlab/infra/kubernetes/jupyterlab/manifests/pvc.yaml

## Create JupyterHub cluster
jupyterhub-cluster:
	helm upgrade --cleanup-on-fail \
		--install jhub jupyterhub/jupyterhub \
		--namespace jhub \
		--version=$(jupyterhub_version) \
		--values /home/daniel/k3s-ray-jupyterlab/infra/kubernetes/jupyterlab/values.yaml \
		--wait --debug

## Expose jupyterhub
jupyterhub-forward:
	kubectl --namespace=jhub port-forward service/proxy-public 8082:80 --address 0.0.0.0