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
DAPR_STORE_NAME = "order-state-store"
logger.info(f"Using Dapr HTTP port: {DAPR_HTTP_PORT}")
logger.info(f"Using Dapr store name: {DAPR_STORE_NAME}")

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """
    Retrieve an order by orderId
    Example: GET /orders/1001
    """
    logger.info(f"GET /orders/{order_id} request")
    order_key = f"order:{order_id}"
    logger.debug(f"Looking up order with key: {order_key}")
    
    with DaprClient() as client:
        try:
            logger.debug(f"Getting state for key: {order_key}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=order_key)
            if not resp.data:
                logger.warning(f"Order not found: {order_id}")
                return jsonify({"error": "Order not found"}), 404
            
            order_data = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Order data retrieved: {order_data}")
            logger.info(f"Successfully retrieved order: {order_id}")
            return jsonify(order_data), 200
        
        except Exception as e:
            logger.error(f"Error in get_order: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/orders', methods=['GET'])
def get_orders_by_user():
    """
    Retrieve all orders for a specific userId
    Example: GET /orders?userId=123
    """
    user_id = request.args.get('userId')
    logger.info(f"GET /orders request with userId: {user_id}")
    
    if not user_id:
        logger.warning("Missing required parameter: userId")
        return jsonify({"error": "userId parameter is required"}), 400
    
    # Create an index key for user orders
    index_key = f"user-orders:{user_id}"
    logger.debug(f"Looking up orders with index key: {index_key}")
    
    with DaprClient() as client:
        try:
            # Get the list of order IDs for this user
            logger.debug(f"Getting order IDs from index key: {index_key}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=index_key)
            
            if not resp.data:
                logger.info(f"No orders found for user: {user_id}")
                return jsonify([]), 200
            
            order_ids = json.loads(resp.data.decode('utf-8'))
            logger.info(f"Found {len(order_ids)} order IDs: {order_ids}")
            
            # Get the order details for each ID
            orders = []
            for order_id in order_ids:
                order_key = f"order:{order_id}"
                logger.debug(f"Getting order details for key: {order_key}")
                
                try:
                    single_resp = client.get_state(store_name=DAPR_STORE_NAME, key=order_key)
                    if single_resp.data:
                        order_data = json.loads(single_resp.data.decode('utf-8'))
                        logger.debug(f"Order data retrieved: {order_data}")
                        orders.append(order_data)
                    else:
                        logger.warning(f"No data found for order ID: {order_id}")
                except Exception as inner_e:
                    logger.error(f"Error retrieving order {order_id}: {str(inner_e)}")
            
            logger.info(f"Returning {len(orders)} orders")
            return jsonify(orders), 200
        
        except Exception as e:
            logger.error(f"Error in get_orders_by_user: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/orders', methods=['POST'])
def create_order():
    """
    Create a new order
    Example request body:
    {
      "orderId": "1001",
      "userId": "123",
      "orderDate": "2023-10-01",
      "totalAmount": 150.00,
      "products": [
        { "productId": "p1", "quantity": 2 },
        { "productId": "p2", "quantity": 1 }
      ]
    }
    """
    order_data = request.json
    logger.info(f"POST /orders request with data: {order_data}")
    
    # Validate required fields
    required_fields = ["orderId", "userId", "orderDate", "totalAmount", "products"]
    for field in required_fields:
        if field not in order_data:
            logger.warning(f"Missing required field in request: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    order_id = order_data["orderId"]
    user_id = order_data["userId"]
    order_key = f"order:{order_id}"
    logger.debug(f"Order key: {order_key}")
    
    with DaprClient() as client:
        try:
            # Check if order already exists
            logger.debug(f"Checking if order already exists: {order_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=order_key)
            if resp.data:
                logger.warning(f"Order already exists: {order_id}")
                return jsonify({"error": "Order already exists"}), 409
            
            # Store the order data
            logger.debug(f"Saving order data for key: {order_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=order_key, value=json.dumps(order_data))
            logger.debug(f"Order data saved successfully")
            
            # Update the user-orders index
            index_key = f"user-orders:{user_id}"
            logger.debug(f"Updating user-orders index for key: {index_key}")
            
            # Get existing index
            index_resp = client.get_state(store_name=DAPR_STORE_NAME, key=index_key)
            if index_resp.data:
                order_ids = json.loads(index_resp.data.decode('utf-8'))
                logger.debug(f"Existing order IDs in index: {order_ids}")
                if order_id not in order_ids:
                    order_ids.append(order_id)
                    logger.debug(f"Added order ID to index: {order_id}")
                else:
                    logger.debug(f"Order ID already exists in index: {order_id}")
            else:
                order_ids = [order_id]
                logger.debug(f"Created new index with order ID: {order_id}")
            
            # Save the updated index
            client.save_state(store_name=DAPR_STORE_NAME, key=index_key, value=json.dumps(order_ids))
            logger.debug(f"Index saved successfully")
            
            logger.info(f"Order created successfully: {order_id}")
            return jsonify(order_data), 201
        
        except Exception as e:
            logger.error(f"Error in create_order: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

@app.route('/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    """
    Update an existing order
    Example: PUT /orders/1001
    Example request body:
    {
      "orderDate": "2023-10-02",
      "totalAmount": 200.00,
      "products": [
        { "productId": "p1", "quantity": 3 }
      ]
    }
    """
    logger.info(f"PUT /orders/{order_id} request")
    update_data = request.json
    logger.debug(f"Update data: {update_data}")
    
    order_key = f"order:{order_id}"
    logger.debug(f"Order key: {order_key}")
    
    with DaprClient() as client:
        try:
            # Check if order exists
            logger.debug(f"Checking if order exists: {order_id}")
            resp = client.get_state(store_name=DAPR_STORE_NAME, key=order_key)
            if not resp.data:
                logger.warning(f"Order not found for update: {order_id}")
                return jsonify({"error": "Order not found"}), 404
            
            # Get existing order data
            existing_order = json.loads(resp.data.decode('utf-8'))
            logger.debug(f"Existing order data: {existing_order}")
            
            # Update order data
            for key, value in update_data.items():
                existing_order[key] = value
            
            # Store the updated order data
            logger.debug(f"Saving updated order data for key: {order_key}")
            client.save_state(store_name=DAPR_STORE_NAME, key=order_key, value=json.dumps(existing_order))
            logger.debug(f"Order data updated successfully")
            
            logger.info(f"Order updated successfully: {order_id}")
            return jsonify(existing_order), 200
        
        except Exception as e:
            logger.error(f"Error in update_order: {str(e)}", exc_info=True)
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
    logger.info("Starting Order Service application")
    logger.info(f"Server running on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
