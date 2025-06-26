# Week 07 - Example 03: Enhanced Monitoring for Product & Order Services

## Running Code

### 1. Build and Push Docker Images to ACR

- Navigate to your `week07/example-3` directory in your terminal and run the following command to build images.

  ```bash
  # Navigate to your product_service directory
  cd week07/example-3/backend/product_service

  # Build the Docker image (ensure your Dockerfile is in this directory)
  docker build -t YOUR_ACR_NAME/product-service:latest .

  # Log in to ACR
  az acr login --username YOUR_ACR_USERNAME --password YOUR_ACR_PASSWORD

  # Push the image to ACR
  docker push YOUR_ACR_NAME/product-service:latest

  # Repeat for order_service
  cd ../order_service
  docker build -t YOUR_ACR_NAME/order-service:latest .
  docker push YOUR_ACR_NAME/order-service:latest
  ```

- **NOTE** : Replace `YOUR_ACR_NAME` with the actual name of your Azure Container Registry.

## Deployment Steps

Navigate to your `week03/example-3/k8s` directory in your terminal.

- Deploy Databases:

  ```bash
  kubectl apply -f product-db.yaml
  kubectl apply -f order-db.yaml
  ```

- Deploy Application Services:

  ```bash
  kubectl apply -f product-service.yaml
  kubectl apply -f order-service.yaml
  ```

- Deploy Prometheus Configuration and RBAC:

  ```bash
  kubectl apply -f prometheus-configmap.yaml
  kubectl apply -f prometheus-rbac.yaml
  ```

- Deploy Prometheus Server:

  ```bash
  kubectl apply -f prometheus-deployment.yaml
  ```

- Deploy Grafana:

  ```bash
  kubectl apply -f grafana-deployment.yaml
  ```

- **NOTE**: Wait for Resources to Spin Up: It may take a few minutes for pods to start and `LoadBalancer` IPs to be assigned. You can monitor progress with `kubectl get pods` and `kubectl get services`.

## Verification

### 1. Get External IP Addresses

```bash
kubectl get services
```

### 2. Verify Application Services

- Product Service Root: `http://<PRODUCT-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/`

- Product Service Health: `http://<PRODUCT-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/health`

- Order Service Root: `http://<ORDER-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/`

- Order Service Health: `http://<ORDER-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/health`

### 3. Verify Prometheus Metrics Endpoints

- Product Service Metrics: `http://<PRODUCT-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/metrics`

- Order Service Metrics: `http://<ORDER-SERVICE-EXTERNAL-IP>:<PORT_NUMBER>/metrics`

### 4. Access and Use Prometheus UI

- Open your browser to: `http://<PROMETHEUS-SERVICE-EXTERNAL-IP>`

- Navigate to `Status` > `Targets`. You should see both `product-service` and `order-service` pods listed as UP.

- Go to the Graph tab and query metrics, e.g., `http_requests_total{app_name="product_service"}`.

### 5. Access and Use Grafana UI

- Open your browser to: `http://<GRAFANA-SERVICE-EXTERNAL-IP>`

- Login: Use username `admin` and password `admin`.

- Verify your Prometheus data source configration.

- Go to Explore and query metrics from both services (e.g., rate(order_creation_total{app_name="order_service"}[1m])).

### 6. Generate Traffic to See Metrics Change

Make API calls to your Product and Order services (e.g., creating products, placing orders). Observe the metrics in Prometheus and Grafana update in real-time.

## Cleanup

To remove all Kubernetes resources deployed in this example, navigate to your `week07/example-3/k8s` directory and run:

```bash
kubectl delete -f .
```
