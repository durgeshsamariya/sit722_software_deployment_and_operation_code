# Week 05 Example 01: Full-Stack Microservice Deployment to Azure Kubernetes Service (AKS)

## Introduction

This example significantly advances our deployment strategies by migrating the multi-service application from a local Kubernetes cluster (like Docker Desktop) to a managed cloud Kubernetes service: **Azure Kubernetes Service (AKS)**. This provides practical experience with deploying containerized applications to a production-grade cloud environment.

You will learn how to:

- Set up essential Azure resources: Resource Group, Azure Container Registry (ACR), and an AKS cluster.
- Integrate ACR with AKS for secure image pulling.
- Build Docker images and push them to your private ACR.
- Configure and apply Kubernetes `ConfigMaps` and `Secrets` within an AKS context.
- Deploy multiple microservices (Product, Order), a messaging queue (RabbitMQ), and a Frontend to AKS.
- Verify the health, networking, and accessibility of your cloud-deployed applications.
- Manage and clean up resources in Azure.

## Azure Setup (Resource Group, ACR, AKS)

Before deploying, you need to set up your Azure environment.

1. **Log in to Azure CLI:**

```
az login
```

Follow the instructions to authenticate.

2. **Create an Azure Resource Group:**

A resource group is a logical container for your Azure resources.

```bash
az group create --name week05_example1_rg --location australiaeast
```

3. **Create an Azure Container Registry (ACR):**

ACR will host your Docker images for deployment to AKS.

```bash
az acr create --resource-group week05_example1_rg --name sit722week05ex1  --sku Basic --admin-enabled true
```

4. **Create an Azure Kubernetes Service (AKS) Cluster:**

This will deploy a small AKS cluster and integrate it with your ACR.

```bash
az aks create --resource-group week05_example1_rg --name sit722week05ex1aks --node-count 1 --generate-ssh-keys --attach-acr sit722week05ex1
```

5.  **Get AKS Cluster Credentials:**

Configure `kubectl` to connect to your new AKS cluster.

```bash
az aks get-credentials --resource-group week05_example1_rg --name sit722week05ex1aks --overwrite-existing
```

This command merges the AKS cluster's credentials into your local `~/.kube/config` file and sets it as the current context for `kubectl`.
