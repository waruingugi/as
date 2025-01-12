# Instructions to setup k8 workers for each app

1. Setup app the namespace.
`kubectl create namespace <namespace-name>`

2. Load the secrets
```
kubectl create secret generic chrome-secrets \
  --from-literal=VNC_PASSWORD='your-vnc-password' \
  --namespace=<namespace-name>
```

```
kubectl create secret docker-registry github-docker-secret \
  --docker-server=ghcr.io \
  --docker-username=<your-github-username> \
  --docker-password=<your-github-token> \
  --docker-email=<your-email@example.com> \
  --namespace=<namespace-name>
```

3. Setup environment variables using envsubst
```
export APP_NAME=<app-name>
export NAMESPACE=<namespace-name>
```

4. Apply configuration to templates
```
envsubst < service-template.yaml | kubectl apply -f -
envsubst < statefulset-template.yaml | kubectl apply -f -
```

# Handy commands
- Get resource usage of pods:
```
kubectl top pod -n <namespace-name>
```

- Get external IP addresses of pods (use RealVNV viewer desktop app to connect remotely):
```
kubectl get svc -n <namespace-name>
```
