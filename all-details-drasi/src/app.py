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
DAPR_STORE_NAME = "composite-state-store"
logger.info(f"Using Dapr HTTP port: {DAPR_HTTP_PORT}")
logger.info(f"Using Dapr store name: {DAPR_STORE_NAME}")

@app.route('/users/<user_id>/all-details-drasi', methods=['GET'])
def get_profile_with_orders(user_id):
    """
    Retrieve a precomputed user profile with order history and product details
    Example: GET /users/123/all-details-drasi
    """
    logger.info(f"GET /users/{user_id}/all-details-drasi request")
    composite_key = f"user:{user_id}"
    logger.debug(f"Looking up composite data with key: {composite_key}")
    
    with DaprClient() as client:
        try:
            # Retrieve precomputed data from the state store
            logger.debug(f"Getting state for key: {composite_key}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=composite_key)
            if not resp.data:
                logger.warning(f"Composite data not found for user: {user_id}")
                return jsonify({"error": "User profile not found"}), 404
            
            composite_data = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Composite data retrieved: {composite_data}")
            logger.info(f"Successfully retrieved profile with orders for user: {user_id}")
            return jsonify(composite_data), 200
        
        except Exception as e:
            logger.error(f"Error in get_profile_with_orders: {str(e)}", exc_info=True)
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
    logger.info("Starting All-Details-Drasi Service application")
    logger.info(f"Server running on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
