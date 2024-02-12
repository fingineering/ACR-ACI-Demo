# Run a Container on Azure Container Instance using Docker-Compose

## Create a Resource Group

Before we start to create actual resources, you might want to create a new
resource group for your resource. If you already have one, you can use an
existing as well. Take not that you can't access an Azure Container Registry in
another Subscription.

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

First we compose the 

```bash
az container create -g ContainerDemo --file deploy-aci.yaml
```
