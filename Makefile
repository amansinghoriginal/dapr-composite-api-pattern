.PHONY: all create-cluster install-dapr deploy-all redeploy-all clean deep-clean \
	deploy-user-service redeploy-user-service clean-user-service port-forward-user-service test-user-service \
	deploy-order-service redeploy-order-service clean-order-service port-forward-order-service test-order-service \
	deploy-product-service redeploy-product-service clean-product-service port-forward-product-service test-product-service \
	deploy-all-details-direct redeploy-all-details-direct clean-all-details-direct port-forward-all-details-direct test-all-details-direct \
	deploy-all-details-drasi redeploy-all-details-drasi clean-all-details-drasi port-forward-all-details-drasi test-all-details-drasi

# Variables
CLUSTER_NAME=dapr-microservices

# Main targets
all: create-cluster install-dapr deploy-all

# Create kind cluster only if it doesn't exist
create-cluster:
	@echo "Checking if kind cluster exists..."
	@if ! kind get clusters | grep -q $(CLUSTER_NAME); then \
		echo "Creating kind cluster..."; \
		kind create cluster --name $(CLUSTER_NAME); \
	else \
		echo "Cluster $(CLUSTER_NAME) already exists"; \
	fi
	kubectl cluster-info

# Install Dapr on the cluster only if not already installed
install-dapr:
	@echo "Checking if Dapr CLI is installed..."
	@which dapr || (echo "Dapr CLI not found. Please install it first: https://docs.dapr.io/getting-started/install-dapr-cli/" && exit 1)
	@echo "Checking if Dapr is already installed on the cluster..."
	@if ! kubectl get namespace dapr-system > /dev/null 2>&1 || ! kubectl get pods -n dapr-system 2>/dev/null | grep -q "Running"; then \
		echo "Installing Dapr on the cluster..."; \
		dapr init -k --wait; \
	else \
		echo "Dapr is already installed on the cluster"; \
	fi

# Deploy all services
deploy-all: deploy-user-service deploy-order-service deploy-product-service deploy-all-details-direct deploy-all-details-drasi
	@echo "All services deployed successfully"

# Redeploy all services
redeploy-all: redeploy-user-service redeploy-order-service redeploy-product-service redeploy-all-details-direct redeploy-all-details-drasi
	@echo "All services redeployed successfully"

# Clean all services but keep the cluster
clean: clean-user-service clean-order-service clean-product-service clean-all-details-direct clean-all-details-drasi
	@echo "All services cleaned successfully"

# Deep clean - remove all services and delete the cluster
deep-clean: clean
	@echo "Deleting kind cluster..."
	kind delete cluster --name $(CLUSTER_NAME)
	@echo "Deep clean completed"

# User Service targets
deploy-user-service:
	@echo "Deploying User Service..."
	@echo "Deploying PostgreSQL for User Service..."
	kubectl apply -f user-service/k8s/postgres.yaml
	@echo "Waiting for PostgreSQL to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/user-postgres || true
	@echo "Deploying Dapr components for User Service..."
	kubectl apply -f user-service/components/
	@echo "Building User Service image..."
	docker build -t user-service:latest ./user-service/src
	kind load docker-image user-service:latest --name $(CLUSTER_NAME)
	@echo "Deploying User Service..."
	kubectl apply -f user-service/k8s/user-service.yaml
	@echo "Waiting for User Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/user-service || true
	@echo "User Service deployed successfully"

redeploy-user-service:
	@echo "Redeploying User Service..."
	@echo "Building User Service image..."
	docker build -t user-service:latest ./user-service/src
	kind load docker-image user-service:latest --name $(CLUSTER_NAME)
	@echo "Removing existing User Service deployment..."
	kubectl delete -f user-service/k8s/user-service.yaml --ignore-not-found=true
	@echo "Deploying User Service..."
	kubectl apply -f user-service/k8s/user-service.yaml
	@echo "Waiting for User Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/user-service || true
	@echo "User Service redeployed successfully"

clean-user-service:
	@echo "Cleaning User Service..."
	kubectl delete -f user-service/k8s/user-service.yaml --ignore-not-found=true
	kubectl delete -f user-service/components/ --ignore-not-found=true
	kubectl delete -f user-service/k8s/postgres.yaml --ignore-not-found=true
	@echo "User Service cleaned successfully"

test-user-service:
	@echo "Testing User Service..."
	@echo ".... hitting health endpoint ...."
	curl http://localhost:8081/health
	@echo ".... creating new user ...."
	curl -X POST http://localhost:8081/users -H "Content-Type: application/json" \
		-d '{ "userId": "123", "name": "Alice", "email": "alice@example.com" }'
	@echo ".... getting user ...."
	curl http://localhost:8081/users/123

port-forward-user-service:
	@echo "Port forwarding User Service to localhost:8081..."
	kubectl port-forward svc/user-service 8081:80 

# Order Service targets
deploy-order-service:
	@echo "Deploying Order Service..."
	@echo "Deploying PostgreSQL for Order Service..."
	kubectl apply -f order-service/k8s/postgres.yaml
	@echo "Waiting for PostgreSQL to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/order-postgres || true
	@echo "Deploying Dapr components for Order Service..."
	kubectl apply -f order-service/components/
	@echo "Building Order Service image..."
	docker build -t order-service:latest ./order-service/src
	kind load docker-image order-service:latest --name $(CLUSTER_NAME)
	@echo "Deploying Order Service..."
	kubectl apply -f order-service/k8s/order-service.yaml
	@echo "Waiting for Order Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/order-service || true
	@echo "Order Service deployed successfully"

redeploy-order-service:
	@echo "Redeploying Order Service..."
	@echo "Building Order Service image..."
	docker build -t order-service:latest ./order-service/src
	kind load docker-image order-service:latest --name $(CLUSTER_NAME)
	@echo "Removing existing Order Service deployment..."
	kubectl delete -f order-service/k8s/order-service.yaml --ignore-not-found=true
	@echo "Deploying Order Service..."
	kubectl apply -f order-service/k8s/order-service.yaml
	@echo "Waiting for Order Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/order-service || true
	@echo "Order Service redeployed successfully"

clean-order-service:
	@echo "Cleaning Order Service..."
	kubectl delete -f order-service/k8s/order-service.yaml --ignore-not-found=true
	kubectl delete -f order-service/components/ --ignore-not-found=true
	kubectl delete -f order-service/k8s/postgres.yaml --ignore-not-found=true
	@echo "Order Service cleaned successfully"

port-forward-order-service:
	@echo "Port forwarding Order Service to localhost:8082..."
	kubectl port-forward svc/order-service 8082:80 

test-order-service:
	@echo "Testing Order Service..."
	@echo ".... hitting health endpoint ...."
	curl http://localhost:8082/health
	@echo ".... creating new order ...."
	curl -X POST http://localhost:8082/orders -H "Content-Type: application/json" \
		 -d '{ "orderId": "1001", "userId": "123", "orderDate": "2023-10-01", "totalAmount": 150.00,\
			"products": [  \
				{"productId": "p1", "quantity": 2 }, \
				{ "productId": "p2", "quantity": 1 } ] }'
	@echo ".... getting order ...."
	curl http://localhost:8082/orders/1001

# Product Service targets
deploy-product-service:
	@echo "Deploying Product Service..."
	@echo "Deploying PostgreSQL for Product Service..."
	kubectl apply -f product-service/k8s/postgres.yaml
	@echo "Waiting for PostgreSQL to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/product-postgres || true
	@echo "Deploying Dapr components for Product Service..."
	kubectl apply -f product-service/components/
	@echo "Building Product Service image..."
	docker build -t product-service:latest ./product-service/src
	kind load docker-image product-service:latest --name $(CLUSTER_NAME)
	@echo "Deploying Product Service..."
	kubectl apply -f product-service/k8s/product-service.yaml
	@echo "Waiting for Product Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/product-service || true
	@echo "Product Service deployed successfully"

redeploy-product-service:
	@echo "Redeploying Product Service..."
	@echo "Building Product Service image..."
	docker build -t product-service:latest ./product-service/src
	kind load docker-image product-service:latest --name $(CLUSTER_NAME)
	@echo "Removing existing Product Service deployment..."
	kubectl delete -f product-service/k8s/product-service.yaml --ignore-not-found=true
	@echo "Deploying Product Service..."
	kubectl apply -f product-service/k8s/product-service.yaml
	@echo "Waiting for Product Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/product-service || true
	@echo "Product Service redeployed successfully"

clean-product-service:
	@echo "Cleaning Product Service..."
	kubectl delete -f product-service/k8s/product-service.yaml --ignore-not-found=true
	kubectl delete -f product-service/components/ --ignore-not-found=true
	kubectl delete -f product-service/k8s/postgres.yaml --ignore-not-found=true
	@echo "Product Service cleaned successfully"

port-forward-product-service:
	@echo "Port forwarding Product Service to localhost:8083..."
	kubectl port-forward svc/product-service 8083:80

test-product-service:
	@echo "Testing Product Service..."
	@echo ".... hitting health endpoint ...."
	curl http://localhost:8083/health
	@echo ".... creating new product ...."
	curl -X POST http://localhost:8083/products -H "Content-Type: application/json" \
		-d '{ "productId": "p1", "name": "Laptop", "description": "High-end laptop", "price": 1000.00 }'
	@echo ".... getting product ...."
	curl http://localhost:8083/products/p1

# Profile Service targets
deploy-all-details-direct:
	@echo "Deploying Profile Service..."
	@echo "Building Profile Service image..."
	docker build -t all-details-direct:latest ./all-details-direct/src
	kind load docker-image all-details-direct:latest --name $(CLUSTER_NAME)
	@echo "Deploying Profile Service..."
	kubectl apply -f all-details-direct/k8s/all-details-direct.yaml
	@echo "Waiting for Profile Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/all-details-direct || true
	@echo "Profile Service deployed successfully"

redeploy-all-details-direct:
	@echo "Redeploying Profile Service..."
	@echo "Building Profile Service image..."
	docker build -t all-details-direct:latest ./all-details-direct/src
	kind load docker-image all-details-direct:latest --name $(CLUSTER_NAME)
	@echo "Removing existing Profile Service deployment..."
	kubectl delete -f all-details-direct/k8s/all-details-direct.yaml --ignore-not-found=true
	@echo "Deploying Profile Service..."
	kubectl apply -f all-details-direct/k8s/all-details-direct.yaml
	@echo "Waiting for Profile Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/all-details-direct || true
	@echo "Profile Service redeployed successfully"

clean-all-details-direct:
	@echo "Cleaning Profile Service..."
	kubectl delete -f all-details-direct/k8s/all-details-direct.yaml --ignore-not-found=true
	@echo "Profile Service cleaned successfully"

port-forward-all-details-direct:
	@echo "Port forwarding Profile Service to localhost:8084..."
	kubectl port-forward svc/all-details-direct 8084:80

test-all-details-direct:
	@echo "Testing Profile Service..."
	@echo ".... hitting health endpoint ...."
	curl http://localhost:8084/health
	@echo ".... creating new user ..."
	curl -X POST http://localhost:8081/users \
		-H "Content-Type: application/json" \
		-d '{ "userId": "test-all-details-direct-123", "name": "Jane Doe", "email": "jane.doe@example.com" }'
	@echo ".... creating products ...."
	curl -X POST http://localhost:8083/products -H "Content-Type: application/json" \
		-d '{ "productId": "test-all-details-direct-p1", "name": "Laptop Pro", "description": "High-end laptop with 16GB RAM", "price": 1299.99 }'
	curl -X POST http://localhost:8083/products -H "Content-Type: application/json" \
		-d '{ "productId": "test-all-details-direct-p2", "name": "Wireless Headphones", "description": "Noise-cancelling wireless headphones", "price": 249.99}'
	curl -X POST http://localhost:8083/products -H "Content-Type: application/json" \
		-d '{ "productId": "test-all-details-direct-p3","name": "Smartphone X", "description": "Latest smartphone model with advanced camera", "price": 899.99}'
	curl -X POST http://localhost:8083/products -H "Content-Type: application/json" \
		-d '{ "productId": "test-all-details-direct-p4", "name": "Tablet Mini", "description": "8-inch tablet perfect for reading and browsing", "price": 399.99 }'
	@echo ".... creating orders ...."
	curl -X POST http://localhost:8082/orders -H "Content-Type: application/json" \
		-d '{ "orderId": "test-all-details-direct-1001", "userId": "test-all-details-direct-123", "orderDate": "2025-03-28", "totalAmount": 1549.98, "products": [ { "productId": "test-all-details-direct-p1", "quantity": 1 }, { "productId": "test-all-details-direct-p2", "quantity": 1 } ] }'
	curl -X POST http://localhost:8082/orders -H "Content-Type: application/json" \
		-d '{"orderId": "test-all-details-direct-1002", "userId": "test-all-details-direct-123", "orderDate": "2025-03-31", "totalAmount": 899.99, "products": [ { "productId": "test-all-details-direct-p3", "quantity": 1 } ] }'
	curl -X POST http://localhost:8082/orders -H "Content-Type: application/json" \
		-d '{ "orderId": "test-all-details-direct-1003", "userId": "test-all-details-direct-123", "orderDate": "2025-04-01", "totalAmount": 1049.97, "products": [ { "productId": "test-all-details-direct-p2", "quantity": 1 }, { "productId": "test-all-details-direct-p4", "quantity": 2 } ] }'
	@echo ".... getting all user details using DIRECT API ...."
	curl localhost:8084/users/test-all-details-direct-123/all-details-direct

# Drasi Service targets
deploy-all-details-drasi:
	@echo "Deploying Drasi Service..."
	@echo "Deploying PostgreSQL for Drasi Service..."
	kubectl apply -f all-details-drasi/k8s/postgres.yaml
	@echo "Waiting for PostgreSQL to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/drasi-postgres || true
	@echo "Deploying Dapr components for Drasi Service..."
	kubectl apply -f all-details-drasi/components/
	@echo "Building Drasi Service image..."
	docker build -t all-details-drasi:latest ./all-details-drasi/src
	kind load docker-image all-details-drasi:latest --name $(CLUSTER_NAME)
	@echo "Deploying Drasi Service..."
	kubectl apply -f all-details-drasi/k8s/all-details-drasi.yaml
	@echo "Waiting for Drasi Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/all-details-drasi || true
	@echo "Drasi Service deployed successfully"

redeploy-all-details-drasi:
	@echo "Redeploying Drasi Service..."
	@echo "Building Drasi Service image..."
	docker build -t all-details-drasi:latest ./all-details-drasi/src
	kind load docker-image all-details-drasi:latest --name $(CLUSTER_NAME)
	@echo "Removing existing Drasi Service deployment..."
	kubectl delete -f all-details-drasi/k8s/all-details-drasi.yaml --ignore-not-found=true
	@echo "Deploying Drasi Service..."
	kubectl apply -f all-details-drasi/k8s/all-details-drasi.yaml
	@echo "Waiting for Drasi Service to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/all-details-drasi || true
	@echo "Drasi Service redeployed successfully"

clean-all-details-drasi:
	@echo "Cleaning Drasi Service..."
	kubectl delete -f all-details-drasi/k8s/all-details-drasi.yaml --ignore-not-found=true
	kubectl delete -f all-details-drasi/components/ --ignore-not-found=true
	kubectl delete -f all-details-drasi/k8s/postgres.yaml --ignore-not-found=true
	@echo "Drasi Service cleaned successfully"

port-forward-all-details-drasi:
	@echo "Port forwarding Drasi Service to localhost:8085..."
	kubectl port-forward svc/all-details-drasi 8085:80

