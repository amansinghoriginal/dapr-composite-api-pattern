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
DAPR_STORE_NAME = "user-state-store"
logger.info(f"Using Dapr HTTP port: {DAPR_HTTP_PORT}")
logger.info(f"Using Dapr store name: {DAPR_STORE_NAME}")

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    Retrieve a user profile by userId
    Example: GET /users/123
    """
    logger.info(f"GET /users/{user_id} request")
    user_key = f"user:{user_id}"
    logger.debug(f"Looking up user with key: {user_key}")
    
    with DaprClient() as client:
        try:
            logger.debug(f"Getting state for key: {user_key}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=user_key)
            if not resp.data:
                logger.warning(f"User not found: {user_id}")
                return jsonify({"error": "User not found"}), 404
            
            user_data = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"User data retrieved: {user_data}")
            logger.info(f"Successfully retrieved user: {user_id}")
            return jsonify(user_data), 200
        
        except Exception as e:
            logger.error(f"Error in get_user: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user
    Example request body:
    {
      "userId": "123",
      "name": "Alice",
      "email": "alice@example.com"
    }
    """
    user_data = request.json
    logger.info(f"POST /users request with data: {user_data}")
    
    # Validate required fields
    required_fields = ["userId", "name", "email"]
    for field in required_fields:
        if field not in user_data:
            logger.warning(f"Missing required field in request: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    user_id = user_data["userId"]
    user_key = f"user:{user_id}"
    logger.debug(f"User key: {user_key}")
    
    with DaprClient() as client:
        try:
            # Check if user already exists
            logger.debug(f"Checking if user already exists: {user_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=user_key)
            if resp.data:
                logger.warning(f"User already exists: {user_id}")
                return jsonify({"error": "User already exists"}), 409
            
            # Store the user data
            logger.debug(f"Saving user data for key: {user_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=user_key, value=json.dumps(user_data))
            logger.debug(f"User data saved successfully")
            
            logger.info(f"User created successfully: {user_id}")
            return jsonify(user_data), 201
        
        except Exception as e:
            logger.error(f"Error in create_user: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Update an existing user profile
    Example: PUT /users/123
    Example request body:
    {
      "name": "Alice Smith",
      "email": "alice.smith@example.com"
    }
    """
    logger.info(f"PUT /users/{user_id} request")
    update_data = request.json
    logger.debug(f"Update data: {update_data}")
    
    user_key = f"user:{user_id}"
    logger.debug(f"User key: {user_key}")
    
    with DaprClient() as client:
        try:
            # Check if user exists
            logger.debug(f"Checking if user exists: {user_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=user_key)
            if not resp.data:
                logger.warning(f"User not found for update: {user_id}")
                return jsonify({"error": "User not found"}), 404
            
            # Get existing user data
            existing_user = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Existing user data: {existing_user}")
            
            # Update user data
            for key, value in update_data.items():
                existing_user[key] = value
            
            # Store the updated user data
            logger.debug(f"Saving updated user data for key: {user_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=user_key, value=json.dumps(existing_user))
            logger.debug(f"User data updated successfully")
            
            logger.info(f"User updated successfully: {user_id}")
            return jsonify(existing_user), 200
        
        except Exception as e:
            logger.error(f"Error in update_user: {str(e)}", exc_info=True)
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
    logger.info("Starting User Service application")
    logger.info(f"Server running on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
