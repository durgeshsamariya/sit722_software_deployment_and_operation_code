# Week 04 Example 02: Full-Stack Microservice Deployment with Kubernetes

## Introduction

This example extends previous weeks' concepts by demonstrating the deployment of a multi-service application (frontend and two backend microservices) onto a local Kubernetes cluster, typically running via Docker Desktop. This setup provides hands-on experience with container orchestration, configuration management, and service discovery within a Kubernetes environment.

You will learn how to:

- Build Docker images for each component.
- Configure Kubernetes `ConfigMaps` for non-sensitive data and `Secrets` for sensitive information.
- Apply Kubernetes YAML manifests to deploy `Deployments` and `Services`.
- Verify the health and status of your deployed applications.
- Clean up all Kubernetes resources after testing.

## Project Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/durgeshsamariya/sit722_software_deployment_and_operation_code.git
    ```
2.  **Navigate to the example directory:**
    ```bash
    cd sit722_software_deployment_and_operation_code/python/week04/example-2
    ```

## 1. Building Docker Images

Before deploying to Kubernetes, we need to build the Docker images for our frontend and microservices. Kubernetes on Docker Desktop can often access images built locally by Docker if they are tagged correctly. We'll use `docker compose build --no-cache` for convenience, which reads your `docker-compose.yml` to build the images.

1.  **Ensure you are in the `week04/example-2` directory.**

2.  **Build the images:**

    ```bash
    docker compose build --no-cache
    ```

## 2. Kubernetes Configuration (ConfigMaps & Secrets)

Kubernetes `ConfigMaps` and `Secrets` are used to manage configuration data and sensitive information separately from your application code and Docker images. You will likely need to adjust these files based on your specific database connection details or other configuration.

### 2.1. Secrets (`secrets.yaml`)

This file contains non-sensitive configuration data, such as database names or API endpoints.

1.  **Open `secrets.yaml`**.

2.  **Encode your actual password to Base64:**

- **Linux/macOS:**

  ```bash
      echo -n "your_strong_password" | base64
  ```

- **Windows (PowerShell):**

  ```powershell
  [System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("your_strong_password"))
  ```

  Replace `"your_strong_password"` with your password.

## 3. Deploying to Kubernetes

Once your Docker images are built and your Kubernetes YAML configuration files (Deployments, Services, ConfigMaps, Secrets) are ready, you can deploy them to your local Kubernetes cluster.

1.  **Ensure your Docker Desktop Kubernetes cluster is running.** You can verify this by checking the Docker Desktop application icon.

2.  **Ensure you are in the `week04/example-2/k8s` directory** which contains all your Kubernetes YAML files.

3.  **Apply all Kubernetes manifests:**
    ```bash
    kubectl apply -f .
    ```
    This command tells `kubectl` to find all YAML files in the current directory (`.`) and apply them to the Kubernetes cluster.

## 4. Verifying Deployment

After applying the manifests, it's essential to verify that all components are running as expected.

1.  **Check the status of your Pods:**

    ```bash
    kubectl get pods
    ```

    You should see pods for `postgres-db`, `product-service`, `order-service`, and `frontend` in a `Running` state. It might take a moment for all of them to start.

2.  **Check the status of your Services:**

    ```bash
    kubectl get services
    ```

    You should see services like `product-service`, `order-service`, `frontend-service`, and `postgres-db`. Pay attention to the `TYPE` (e.g., `ClusterIP`, `NodePort`) and the `PORTS`. For `NodePort` services, you will see a public port listed (e.g., `80:30000/TCP`).

## 5. Accessing the Applications

To access your deployed applications from your local machine:

1.  **Frontend (Product Catalog):**

    - Find the `NodePort` assigned to your `frontend-service` (e.g., from `kubectl get services`). It's `30002`.
    - Open your web browser and go to `http://localhost:30002`.
    - The frontend will communicate with the backend services internally within the Kubernetes cluster.

2.  **Backend API (Product Service - Swagger UI):**

    - Find the `NodePort` assigned to your `product-service`.
    - Open your web browser and go to `http://localhost:30000/docs`.

3.  **Backend API (Order Service - Swagger UI):**
    - Find the `NodePort` assigned to your `order-service`.
    - Open your web browser and go to `http://localhost:30001/docs`.

You can now interact with the frontend to add and view products/orders, which will communicate through the Kubernetes services to your backend microservices and database.

## 6. Cleaning Up Kubernetes Deployments

To stop and remove all services, deployments, and associated Docker resources created by Kubernetes, use the `kubectl delete` command.

1.  **Ensure you are in the `week04/example-2/k8s` directory.**

2.  **Delete all Kubernetes manifests:**
    ```bash
    kubectl delete -f .
    ```
    This command will delete all resources defined in the YAML files within the current directory. This is crucial for a clean slate before your next deployment or when you are done with the example.
