# Helm Deployment Guide for as-workers
This guide provides step-by-step instructions for deploying and managing your worker applications (betika, betgr8, etc.) using the as-workers Helm chart.

## 1. Prerequisites
Before you begin, ensure the following are in place:
- unzip
- A Kubernetes cluster is running and accessible.
- kubectl is installed and configured to interact with your cluster.
- Helm is installed (v3 or later).
- Necessary secrets are created via kubectl (optional if secrets are created outside the chart).

## 2. Chart Structure
The as-workers Helm chart contains templates for:
- Namespaces
- StatefulSets
- Services
- Service Accounts
- RBAC roles and bindings
- Dynamic configuration using values.yaml.

## 3. Deployment Steps
### Step 1: Install the Helm Chart
Download the helm as a zip folder(if you haven't zipped it, the folder is `k8/workers`) and in your k8 cluster unzip it:
```
unzip workers.zip -d workers
```

Deploy the chart for a specific app (e.g., betika):
```
helm install <app>-workers ./workers \
  --set app=<app> \
  --set dockerRegistry.username=<> \
  --set dockerRegistry.password=<> \
  --set dockerRegistry.email=<> \
  --set secrets.pod0.API_KEY=<> \
  --set secrets.pod0.PHONE_NUMBER=<> \
  --set secrets.pod0.PASSWORD=<> \
  --set secrets.pod1.API_KEY=<> \
  --set secrets.pod1.PHONE_NUMBER=<> \
  --set secrets.pod1.PASSWORD=<> \
  --set secrets.pod2.API_KEY=<> \
  --set secrets.pod2.PHONE_NUMBER=<> \
  --set secrets.pod2.PASSWORD=<> \
  --set secrets.VNC_PASSWORD=<> \
  --set secrets.BASE_URL=<>
```
Replace `<app>` with the app name (e.g., betgr8).


### Step 2: Verify the Deployment
#### Check Resources:
Ensure the namespace and resources are created:
```
kubectl get all -n <app>
```
Replace `<app>` with the app name e.g `betika`.

List Services: Confirm that services are set up:
```
kubectl get svc -n <app>
```

Check Pods: Verify StatefulSet pods:
```
kubectl get pods -n <app>
```

### Step 3: Create Secrets (Optional)
If secrets are not managed by Helm, create them manually:
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

# 4. RBAC Configuration
RBAC resources are included in the Helm chart.

#### Apply the RBAC Configuration:
This is part of the chart deployment, but you can verify permissions with the `kubectl auth can-i` command.

All responses should be `yes`:
```
kubectl auth can-i delete pods --as=system:serviceaccount:default:pod-restart-sa
kubectl auth can-i delete pods --all-namespaces --as=system:serviceaccount:default:pod-restart-sa
```

#### Retrieve the Token:
Use the following command to retrieve the base64-decoded token for API calls:
```
kubectl -n default get secret pod-restart-token -o jsonpath="{.data.token}" | base64 --decode
```

#### Cluster Endpoint:
Get the Kubernetes cluster endpoint for API interactions:
```
kubectl get endpoints | grep kubernetes
```

### 5. Managing Resources
Check Resource Usage:
```
kubectl top pod -n <namespace-name>
```

View Pod Logs:
```
kubectl logs <pod-name> -n <namespace-name>
```

Stream Logs:
```
kubectl logs -f <pod-name> -n <namespace-name>
```

Check Environment Variables:
```
kubectl exec <pod-name> -n <namespace-name> -- printenv
```

This will display only the events related to the specified Service.
```
kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp' | grep <service-name>
```

### 6. Upgrading or Deleting a Release
#### Upgrade a Release
Always ensure the required secrets are created before deploying the chart.
Use `helm list` to track all deployed releases.

#### To apply changes to the chart:
```
helm upgrade <release-name> ./workers --description <some-description> \
  --set app=<app> \
  --set dockerRegistry.username=<> \
  --set dockerRegistry.password=<> \
  --set dockerRegistry.email=<> \
  --set secrets.pod0.API_KEY=<> \
  --set secrets.pod0.PHONE_NUMBER=<> \
  --set secrets.pod0.PASSWORD=<> \
  --set secrets.pod1.API_KEY=<> \
  --set secrets.pod1.PHONE_NUMBER=<> \
  --set secrets.pod1.PASSWORD=<> \
  --set secrets.pod2.API_KEY=<> \
  --set secrets.pod2.PHONE_NUMBER=<> \
  --set secrets.pod2.PASSWORD=<> \
  --set secrets.VNC_PASSWORD=<> \
  --set secrets.BASE_URL=<>
```

#### To view the release:
```
helm history <release-name>
```

#### Delete a Release
When you run helm uninstall, it completely removes the release by default. However, if you want to keep the release history so you can roll back or inspect past releases, you should use the `--keep-history` flag.
```
helm uninstall <release-name> --keep-history
```
This will delete all resources in the app's namespace.

## Notes
We use betterstack to monitor our k8s (remember to use the disable TLS installation version). 
### Handy commands that may save you errors are:
```
kubectl annotate apiservice v1beta1.metrics.k8s.io   meta.helm.sh/release-name=betterstack-logs   meta.helm.sh/release-namespace=default --overwrite
```

```
kubectl label apiservice v1beta1.metrics.k8s.io   app.kubernetes.io/managed-by=Helm --overwrite
```

#### When deploying a second app
When deploying a second app, helm might block you from doing so due to ownership conflicts.
To resolve this, use the following command:
```
kubectl get clusterrole,clusterrolebinding,secret -A -o json | jq -r '
  .items[] 
  | select(.metadata.annotations["meta.helm.sh/release-name"] == "<app>-workers") 
  | "kubectl annotate " + .kind + " " + .metadata.name + " meta.helm.sh/release-name=<app>-workers meta.helm.sh/release-namespace=default --overwrite"
' | bash
```
where `<app>` is the name of the app you are deploying.  

or you can simply opt to delete the secret token and recreate it BUT remember to update the token on the server:  
```
kubectl delete serviceaccount pod-restart-sa -n default
```
