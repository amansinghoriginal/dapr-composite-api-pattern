import json
import os
import logging
import sys
from flask import Flask, request, jsonify
from dapr.clients import DaprClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Dapr configuration
DAPR_HTTP_PORT = os.getenv("DAPR_HTTP_PORT", "3500")
DAPR_STORE_NAME = "product-state-store"
logger.info(f"Using Dapr HTTP port: {DAPR_HTTP_PORT}")
logger.info(f"Using Dapr store name: {DAPR_STORE_NAME}")

@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """
    Retrieve a product by productId
    Example: GET /products/p1
    """
    logger.info(f"GET /products/{product_id} request")
    product_key = f"product:{product_id}"
    logger.debug(f"Looking up product with key: {product_key}")
    
    with DaprClient() as client:
        try:
            logger.debug(f"Getting state for key: {product_key}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=product_key)
            if not resp.data:
                logger.warning(f"Product not found: {product_id}")
                return jsonify({"error": "Product not found"}), 404
            
            product_data = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Product data retrieved: {product_data}")
            logger.info(f"Successfully retrieved product: {product_id}")
            return jsonify(product_data), 200
        
        except Exception as e:
            logger.error(f"Error in get_product: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/products', methods=['POST'])
def create_product():
    """
    Create a new product
    Example request body:
    {
      "productId": "p1",
      "name": "Laptop",
      "description": "High-end laptop",
      "price": 1000.00
    }
    """
    product_data = request.json
    logger.info(f"POST /products request with data: {product_data}")
    
    # Validate required fields
    required_fields = ["productId", "name", "description", "price"]
    for field in required_fields:
        if field not in product_data:
            logger.warning(f"Missing required field in request: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    product_id = product_data["productId"]
    product_key = f"product:{product_id}"
    logger.debug(f"Product key: {product_key}")
    
    with DaprClient() as client:
        try:
            # Check if product already exists
            logger.debug(f"Checking if product already exists: {product_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=product_key)
            if resp.data:
                logger.warning(f"Product already exists: {product_id}")
                return jsonify({"error": "Product already exists"}), 409
            
            # Store the product data
            logger.debug(f"Saving product data for key: {product_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=product_key, value=json.dumps(product_data))
            logger.debug(f"Product data saved successfully")
            
            logger.info(f"Product created successfully: {product_id}")
            return jsonify(product_data), 201
        
        except Exception as e:
            logger.error(f"Error in create_product: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update an existing product
    Example: PUT /products/p1
    Example request body:
    {
      "name": "Updated Laptop",
      "price": 1200.00
    }
    """
    logger.info(f"PUT /products/{product_id} request")
    update_data = request.json
    logger.debug(f"Update data: {update_data}")
    
    product_key = f"product:{product_id}"
    logger.debug(f"Product key: {product_key}")
    
    with DaprClient() as client:
        try:
            # Check if product exists
            logger.debug(f"Checking if product exists: {product_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=product_key)
            if not resp.data:
                logger.warning(f"Product not found for update: {product_id}")
                return jsonify({"error": "Product not found"}), 404
            
            # Get existing product data
            existing_product = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Existing product data: {existing_product}")
            
            # Update product data
            for key, value in update_data.items():
                existing_product[key] = value
            
            # Store the updated product data
            logger.debug(f"Saving updated product data for key: {product_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=product_key, value=json.dumps(existing_product))
            logger.debug(f"Product data updated successfully")
            
            logger.info(f"Product updated successfully: {product_id}")
            return jsonify(existing_product), 200
        
        except Exception as e:
            logger.error(f"Error in update_product: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    logger.info("GET /health request received")
    logger.debug("Performing health check")
    
    # You could add more comprehensive health checks here
    # For example, checking if Dapr state store is accessible
    
    logger.info("Health check successful")
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    logger.info("Starting Product Service application")
    logger.info(f"Server running on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
