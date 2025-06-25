# Week 07 - Example 02: Enhanced Monitoring for Product & Order Services

## Running Code

- Navigate to your `week07/example-2` directory in your terminal and run the following command to build and start all services:

```bash
docker compose up -d --build
```

## Verification

### 1. Verify Product Service Metrics Endpoint

- Open your web browser and go to: `http://localhost:8000/metrics`

- You should see a page displaying raw Prometheus metrics data.

### 2. Generate Traffic

- To see metrics change, interact with your Product Service. You can do via frontend running locally that calls the Product Service or you can use curl or your browser to hit some endpoints.

- Refresh `http://localhost:8000/metrics` after making requests to see the metric values update.

### 3. Prometheus UI Verification

- Open your web browser and go to: `http://localhost:9090`

- Navigate to `Status` > `Targets`. You should see product-service listed with a state of `UP`.

- Go to the Graph tab. In the "Expression" input, type `http_requests_total` and click "Execute". You should see a graph (or a table of results) if you've made any requests.

### 4. Grafana UI Setup & Verification

- Open your web browser and go to: `http://localhost:3000`

- Login: Use username `admin` and password `admin` (as configured in `docker-compose.yml`). You'll likely be prompted to change the password. You can skip that.

- Add Prometheus Data Source:

  - Click the `Connection` on the left sidebar, then Data sources.

  - Click `Add data source` -> Select `Prometheus`.

  - For the HTTP section, set the URL to `http://prometheus:9090` (this is the Prometheus service name and port within the Docker Compose network).

  - Click Save & test. You should see a "Data source is working" message.

- Explore Metrics

  - Click `Explore` on the left sidebar.

  - Select your newly added Prometheus data source.

  - In the "Metric" field, start typing `http_requests_total`. Select it and click "Run query". You should see a graph of requests over time.

## Cleanup

To stop and remove all Docker containers, networks, and volumes created by Docker Compose:

```bash
docker compose down -v
```
