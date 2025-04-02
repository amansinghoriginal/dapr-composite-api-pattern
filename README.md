# Dapr Composite API Pattern

This project contains five microservices built with Dapr for state management and service invocation.
All services are deployed on a local kind Kubernetes cluster with PostgreSQL databases configured as their state stores.

## Services Overview

1. **User Service**: Manages user profiles
2. **Order Service**: Manages orders placed by users
3. **Product Service**: Manages product information
4. **Profile-With-Orders-Direct**: Aggregates user profiles with orders using direct API calls
5. **Profile-With-Orders-Drasi**: Provides the same aggregated view using Drasi

## Prerequisites
Before you begin, ensure you have the following tools installed:

- Docker
- kubectl
- kind (Kubernetes in Docker)
- Dapr CLI

## Project Structure

```
dapr-composite-api-pattern/
├── Makefile              # Common Makefile for all services
├── user-service/         # User profile management service
│   ├── components/       # Dapr components for User Service
│   ├── k8s/              # Kubernetes manifests
│   └── src/              # Source code
├── order-service/        # Order management service
│   ├── components/
│   ├── k8s/
│   └── src/
├── product-service/      # Product information service
│   ├── components/
│   ├── k8s/
│   └── src/
├── all-details-direct/   # Serves all orders by a user including product details along with their user-profile (direct API calls)
│   ├── k8s/
│   └── src/
└── all-details-drasi/    # Serves all orders by a user including product details along with their user-profile (precomputed data)
    ├── components/
    ├── k8s/
    └── src/
```

## Deployment

The included Makefile automates the entire deployment process with idempotent operations:

### Deploy Everything

To set up the entire stack (kind cluster, Dapr, and all services):

```bash
cd dapr-microservices
make all
```

This command will:
- Create a kind cluster named "dapr-composite-api-pattern" (only if it doesn't already exist)
- Install Dapr on the cluster (only if it's not already installed)
- Deploy PostgreSQL instances with CDC enabled for each service that needs it
- Deploy Dapr components for all services
- Build and load all service Docker images
- Deploy all services to the cluster

### Access the Services

To access the services, use the port-forwarding commands:

```bash
# User Service
make port-forward-user-service  # Available at http://localhost:8081

# Order Service
make port-forward-order-service  # Available at http://localhost:8082

# Product Service
make port-forward-product-service  # Available at http://localhost:8083

# All Details Service (using Direct API calls)
make port-forward-all-details-direct  # Available at http://localhost:8084

# All Details Service (using Drasi)
make port-forward-all-details-drasi  # Available at http://localhost:8085
```

### Redeploy Services

To redeploy a specific service after making changes:

```bash
make redeploy-user-service
make redeploy-order-service
make redeploy-product-service
make redeploy-all-details-direct
make redeploy-all-details-drasi
```

To redeploy all services:

```bash
make redeploy-all
```

### Clean Up

To clean up all services but keep the cluster:

```bash
make clean
```

To delete the entire kind cluster:

```bash
make deep-clean
```

## Service Details

### User Service

**Purpose**: Manages user profiles, allowing creation, retrieval, and updates of user information.

**Data Model**:
- Key: `user:{userId}` (e.g., `user:123`)
- Value: JSON object containing user details.

**API Endpoints**:
- `GET /users/{userId}`: Retrieve a user profile by userId
- `POST /users`: Create a new user
- `PUT /users/{userId}`: Update an existing user profile

### Order Service

**Purpose**: Manages orders, including creation, retrieval, and updates, with the ability to filter by user.

**Data Model**:
- Key: `order:{orderId}` (e.g., `order:1001`)
- Value: JSON object containing order details
- Index: `user-orders:{userId}` for querying orders by user

**API Endpoints**:
- `GET /orders/{orderId}`: Retrieve an order by orderId
- `GET /orders?userId={userId}`: Retrieve all orders for a specific userId
- `POST /orders`: Create a new order
- `PUT /orders/{orderId}`: Update an existing order

### Product Service

**Purpose**: Manages product information, including creation, retrieval, and updates.

**Data Model**:
- Key: `product:{productId}` (e.g., `product:p1`)
- Value: JSON object containing product details

**API Endpoints**:
- `GET /products/{productId}`: Retrieve a product by productId
- `POST /products`: Create a new product
- `PUT /products/{productId}`: Update an existing product

### All-Details-Direct Service

**Purpose**: Aggregates data from the User, Order, and Product services by making direct API calls to provide a unified view.

**Implementation Details**:
- Fetches user data from User Service
- Fetches orders from Order Service
- Fetches product details from Product Service
- Combines the data into a single response

**API Endpoints**:
- `GET /users/{userId}/all-details-direct`: Retrieve a user's profile with their order history and product details

### All-Details-Drasi Service

**Purpose**: Provides the same aggregated view as the direct API version but uses a precomputed dataset maintained in a Dapr state store.

**Implementation Details**:
- Retrieves precomputed data using the key `user:{userId}`
- No direct calls to other services are needed

**API Endpoints**:
- `GET /users/{userId}/all-details-drasi`: Retrieve a precomputed user profile with order history and product details

## PostgreSQL CDC Configuration

All PostgreSQL deployments are configured with Change Data Capture (CDC) enabled through the following settings:

- `wal_level=logical` - Enables logical decoding of the WAL stream, required for CDC
- `max_wal_senders=8` - Allows up to 8 concurrent connections for WAL streaming
- `max_replication_slots=4` - Supports up to 4 replication slots for CDC consumers

These settings make the PostgreSQL databases compatible with Debezium and other CDC tools that can capture and stream database changes in real-time.

## Dapr Integration

All services use Dapr for:

1. **State Management**: PostgreSQL state stores for persisting data
2. **Service Invocation**: Direct service-to-service communication

### State Store Components

- **User Service**: `user-state-store`
- **Order Service**: `order-state-store`
- **Product Service**: `product-state-store`
- **All Details with Drasi Service**: `drasi-state-store`

## Troubleshooting

- If you encounter issues with Dapr initialization, ensure the Dapr CLI is properly installed.
- If PostgreSQL deployments fail, check the pod logs with `kubectl logs deployment/<postgres-deployment-name>`.
- For service issues, check the logs with `kubectl logs deployment/<service-name>`.
- Ensure all Kubernetes resources are in the same namespace (default in this setup).
- If you encounter build issues with Docker images, verify that the Python dependencies in `requirements.txt` are correct.
