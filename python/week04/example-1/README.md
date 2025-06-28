# Week 04 - Example 1: Deploying a Single Microservice to Kubernetes

This example focuses on the absolute basics of deploying a single FastAPI microservice to a local Kubernetes cluster. It simplifies the setup by directly embedding environment variables, using the `default` namespace, and connecting to a PostgreSQL database running on your host machine. The frontend will also run locally on your host and connect to the Kubernetes-exposed service.

### 1. Build and Tag Your Product Service Docker Image

Navigate to your `week04/example-1/backend/product_service` directory in your terminal:

```bash
cd week04/example-1/product_service
```

Build the Docker image for your Product Service.

```bash
docker build --no-cache -t product-service-w4e1:latest .
```

### 2. Apply Kubernetes Manifests

Navigate to your `week04/example-1/k8s` directory:

```bash
cd /week04/example-1/k8s
```

Apply the Kubernetes YAML files. These will deploy the Product Service Deployment and expose it via a Service in the default namespace.

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 3. Verify Deployment

Check if the Product Service pod and service are running:

```bash
kubectl get pods
kubectl get services
```

You should see a pod like `product-service-w04e1-xxxxx-xxxxx` and a service named `product-service-w04e1` with a NodePort on port `30000`.

### 4. Access the Product Microservice from Localhost

The Product Microservice will be exposed via the NodePort service.

Product Microservice will be accessible at `http://localhost:30000`.
