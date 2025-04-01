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
logger.info(f"Using Dapr HTTP port: {DAPR_HTTP_PORT}")

@app.route('/users/<user_id>/all-details-direct', methods=['GET'])
def get_profile_with_orders(user_id):
    """
    Retrieve a user's profile with their order history and product details
    Example: GET /users/123/all-details-direct
    """
    logger.info(f"GET /users/{user_id}/all-details-direct request")
    
    with DaprClient() as client:
        try:
            # Step 1: Fetch User Data from User Service
            logger.debug(f"Fetching user data for user ID: {user_id}")
            user_resp = client.invoke_method(
                app_id="user-service",
                method_name=f"users/{user_id}",
                http_verb="GET"
            )
            
            # Check if we have user data
            if not user_resp.data:
                logger.warning(f"User not found: {user_id}")
                return jsonify({"error": "User not found"}), 404
            
            user_data = json.loads(user_resp.data.decode('utf-8'))
            logger.debug(f"User data retrieved: {user_data}")
            
            # Step 2: Fetch Orders from Order Service
            logger.debug(f"Fetching orders for user ID: {user_id}")
            orders_resp = client.invoke_method(
                app_id="order-service",
                method_name=f"orders?userId={user_id}",
                http_verb="GET"
            )
            
            # Check if we have orders data
            if not orders_resp.data:
                logger.warning(f"No orders found for user: {user_id}")
                orders = []
            else:
                orders = json.loads(orders_resp.data.decode('utf-8'))
                logger.debug(f"Retrieved {len(orders)} orders")
            
            # Step 3: Fetch Product Details for each product in the orders
            enriched_orders = []
            for order in orders:
                enriched_products = []
                for product_item in order.get("products", []):
                    product_id = product_item.get("productId")
                    if product_id:
                        logger.debug(f"Fetching product details for product ID: {product_id}")
                        try:
                            product_resp = client.invoke_method(
                                app_id="product-service",
                                method_name=f"products/{product_id}",
                                http_verb="GET"
                            )
                            
                            if product_resp.data:
                                product_data = json.loads(product_resp.data.decode('utf-8'))
                                # Merge product details with quantity from order
                                enriched_product = {
                                    "productId": product_id,
                                    "name": product_data.get("name", "Unknown"),
                                    "price": product_data.get("price", 0),
                                    "quantity": product_item.get("quantity", 0)
                                }
                                enriched_products.append(enriched_product)
                            else:
                                logger.warning(f"Product not found: {product_id}")
                                # Include basic info if product details not found
                                enriched_products.append({
                                    "productId": product_id,
                                    "name": "Unknown Product",
                                    "price": 0,
                                    "quantity": product_item.get("quantity", 0)
                                })
                        except Exception as e:
                            logger.warning(f"Error fetching product {product_id}: {str(e)}")
                            enriched_products.append({
                                "productId": product_id,
                                "name": "Unknown Product",
                                "price": 0,
                                "quantity": product_item.get("quantity", 0)
                            })
                
                # Create enriched order with detailed product information
                enriched_order = {
                    "orderId": order.get("orderId"),
                    "orderDate": order.get("orderDate"),
                    "totalAmount": order.get("totalAmount"),
                    "products": enriched_products
                }
                enriched_orders.append(enriched_order)
            
            # Step 4: Combine everything into the final response
            profile_with_orders = {
                "userId": user_data.get("userId"),
                "name": user_data.get("name"),
                "email": user_data.get("email"),
                "orders": enriched_orders
            }
            
            logger.info(f"Successfully retrieved profile with orders for user: {user_id}")
            return jsonify(profile_with_orders), 200
        
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
    # For example, checking if all dependent services are accessible
    
    logger.info("Health check successful")
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    logger.info("Starting all-details-direct Service application")
    logger.info(f"Server running on 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
