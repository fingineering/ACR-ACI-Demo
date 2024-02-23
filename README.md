# Run a Container on Azure Container Instance using Docker-Compose

Let's say you have build and application, a simple one and you want easily run it on the Azure cloud. But it consists of multiple parts that you want to run in seperate containers. Now you have some options, like an Azure Kubernetes Cluster, or an Azure App Service plus some additional resources, or you create an Azure Container Instance. Simply run a container in the cloud, no complex infrastructure, no complex configuration.

In the following example we start with creating a container registry and build a container group using Azure Container Instance to host a very simple example api with a caddy proxy to add HTTPS traffic encryption. The configuration will set you back $1.30 per day. Not the cheapest option to host an api, but very easy and will update your application as you update the container in the registry.

## Create a Resource Group

Before we start creating actual resources, you might want to create a new
resource group for your resource. If you already have one, you can use an
existing as well. Take notice that you can't access an Azure Container Registry in
another Subscription, except for public Container Registry, therefore we will need to host all resources in one Azure Subscription.

```bash
az group create -n ContainerDemo -l westeurope
```

## Create an Azure Container Instance

Before we create a Container Instance, we need a managed identity for the
Container Instance. We could use a system Assigned Managed Identity, but in
practice it is more handy to use a User Defined Managed Identity. So, first
create a Managed Identity and then a Container Instance.

```bash
az identity create --name DemoContainerInstance --resource-group ContainerDemo
```

Export the Client ID and the Id of the newly created managed identity to variables:

```bash
ACI_ID=$(az identity list -g ContainerDemo | jq -r '.[0].id')
ACI_CLIENT_ID=$(az identity list -g ContainerDemo | jq -r '.[0].clientId')
```

## Create an Azure Container Registry

```bash
az acr create -m demoregistrydq -g ContainerDemo --sku Basic -l westeurope

ACR_ID=$(az acr list -g ContainerDemo | jq -r '.[].id')
```

Make sure that you are allow to push an pull to and from the registry

```bash
MY_ID=$(az account show | jq -r '.user.name')

az role assignment create --assignee $MY_ID role "AcrPush" --scope $ACR_ID
az role assignment create --assignee $MY_ID role "AcrPull" --scope $ACR_ID
```

If you don't have sufficient permissions to assign roles to resource, get someone with elevated permissions.

Now lets add a system assigned managed identity to the container registry

```bash
az acr identity assign --identities '[system]' -n demoregistrydq -g ContainerDemo
```

## Push the container image to the Azure Container Registry

If you are not on a linux/amd64 platform make sure to set the default platform
to `linux/amd64`. This is also recognized by docker compose, which does not
support the platform flag.

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
```

Now you can test the docker build locally with

```bash
docker compose up --build -d
```

And push to the Azure Container Registry

```bash
az acr login
docker compose push
```

## Allow Container Instance to pull from ACR

Bevor the container will successfully run, the Container Instance needs to be
able to pull from the Azure Container Registry. Therefore the ACI needs to have
the role `AcrPull` on the respective Azure Container Registry.

1. Get the id of the managed identity of the Azure Container Instance
2. Ge the scope, which is the Id of the Azure Container Registry
3. Apply the role via Azure CLI

```bash
az role assignment create --assignee $ACI_CLIENT_ID --role "AcrPull" --scope $ACR_ID
```

## Create the container Instance

To run a multi container application, we need to use the deployment via yaml strategy. Use the following YAML to set up the example. In [References](#references) section you can find a link to the full YAML-Reference for Azure Container Registry.

```yaml
apiVersion: '2021-10-01'
location: westeurope
name: dqdemocontainer
identity:
  type: UserAssigned
  userAssignedIdentities:
    '/subscriptions/<subscription id>/resourcegroups/ContainerDemo/providers/Microsoft.ManagedIdentity/userAssignedIdentities/DQDemoContainer':
      clientId: 'client id of the usesr assigned ManagedIdentity'
      principalId: 'principal id of the user assigned ManagedIdentity'
properties:
  imageRegistryCredentials:
  - server: demoregistrydq.azurecr.io
    identity: "/subscriptions/<subscription id>/resourcegroups/ContainerDemo/providers/Microsoft.ManagedIdentity/userAssignedIdentities/DQDemoContainer"
  sku: Standard
  containers:
  - name: fastapi
    properties:
      image: demoregistrydq.azurecr.io/myfastapi:latest
      resources:
        requests:
          cpu: 1
          memoryInGb: 1.5
      ports:
      - port: 8000
  - name: caddy-sidecar
    properties:
      image: demoregistrydq.azurecr.io/mycaddy:latest
      resources:
        requests:
          cpu: 1
          memoryInGb: 1.5
      ports:
      - port: 80
      - port: 443
  osType: Linux
  ipAddress:
    type: Public
    ports:
    - protocol: tcp
      port: 80
    - protocol: tcp
      port: 443
tags: {exampleTag: tutorial}
type: Microsoft.ContainerInstance/containerGroups
```

With the above YAML file, you can easily create your container group via:

```bash
az container create -g ContainerDemo --file deploy-aci.yaml
```

## References

- [YAML Reference for Azure Container Instances](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-reference-yaml)
- [Azure CLI container reference](https://learn.microsoft.com/en-us/cli/azure/container?view=azure-cli-latest)