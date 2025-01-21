# Instructions to setup k8 workers for each app

1. Setup app the namespace.
`kubectl create namespace <namespace-name>`

2. Load the secrets, with values
```
kubectl create secret generic chrome-secrets \
  --from-literal=pod-0-API_KEY=<> \
  --from-literal=pod-0-PHONE_NUMBER=<> \
  --from-literal=pod-0-PASSWORD=<> \
  --from-literal=pod-1-API_KEY=<> \
  --from-literal=pod-1-PHONE_NUMBER=<> \
  --from-literal=pod-1-PASSWORD=<> \
  --from-literal=pod-2-API_KEY=<> \
  --from-literal=pod-2-PHONE_NUMBER=<> \
  --from-literal=pod-2-PASSWORD=<> \
  --from-literal=VNC_PASSWORD=<> \
  --from-literal=BASE_URL=<> \
  --from-literal=APP_NAME=<> \
  --namespace=<>
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

- Check the Environment Variables in the Pod:
```
kubectl exec <pod-name> -n ${APP_NAME} -- printenv
```

- To view the logs of a specific Pod:
```
kubectl logs <pod-name> -n <namespace>
```

- To continuously stream the logs (like tail -f):
```
kubectl logs -f <pod-name> -n <namespace>
```

- This will display only the events related to the specified Service.
```
kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp' | grep <service-name>
```
