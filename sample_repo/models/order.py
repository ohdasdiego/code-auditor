"""
📦 Order Management Module

This module handles order processing and management.
Note that this is a core business logic module.
"""

import datetime
import json
import uuid

# ============================================================
# 📋 Order Status Constants
# ============================================================

# Order has been created
STATUS_CREATED = "created"

# Order is being processed
STATUS_PROCESSING = "processing"

# Order has been completed
STATUS_COMPLETED = "completed"

# Order has been cancelled
STATUS_CANCELLED = "cancelled"


class OrderManager:
    """
    This class manages orders in the system.
    
    Of course, this is the main class for all order-related operations.
    It handles creating, updating, and processing orders.
    """
    
    def __init__(self):
        """
        This method initializes the OrderManager.
        
        Returns:
            None
        """
        # Initialize the orders dictionary
        self.orders = {}
        
        # Initialize the order count
        self.order_count = 0
        
        print("✅ OrderManager initialized successfully!")

    def createOrder(self, customer_id, items, total_amount):
        """
        This method creates a new order.
        
        Args:
            customer_id: The ID of the customer
            items: A list of items in the order
            total_amount: The total amount of the order
            
        Returns:
            The newly created order dictionary
        """
        print("Starting createOrder...")
        
        # Generate a unique order ID
        order_id = str(uuid.uuid4())
        
        # Get the current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Create the order dictionary
        order = {
            "id": order_id,
            "customer_id": customer_id,
            "items": items,
            "total_amount": total_amount,
            "status": STATUS_CREATED,
            "created_at": timestamp,
        }
        
        # Add the order to the orders dictionary
        self.orders[order_id] = order
        
        # Increment the order count
        self.order_count += 1
        
        print(f"✅ Order created successfully: {order_id}")
        return order

    def updateOrder(self, order_id, updates):
        """
        This method updates an existing order.
        
        Args:
            order_id: The ID of the order to update
            updates: A dictionary of fields to update
            
        Returns:
            The updated order dictionary or None if not found
        """
        # Check if the order exists
        if order_id not in self.orders:
            # TODO: add proper error handling
            return None
        
        # Get the existing order
        order = self.orders[order_id]
        
        # Apply the updates
        for key, value in updates.items():
            order[key] = value
        
        # Update the modified timestamp
        order["updated_at"] = datetime.datetime.now().isoformat()
        
        # Return the updated order
        return order

    def deleteOrder(self, order_id):
        """
        This method deletes an order.
        
        Args:
            order_id: The ID of the order to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Check if order exists
        if order_id in self.orders:
            # Delete the order
            del self.orders[order_id]
            # Decrement the count
            self.order_count -= 1
            # Return success
            return True
        # Return failure
        return False

    def processOrder(self, order_id):
        """
        This method processes an order.
        
        Note that this is the main processing function.
        Feel free to extend this with additional processing steps.
        
        Args:
            order_id: The ID of the order to process
            
        Returns:
            The processed order or None on failure
        """
        print(f"Processing order {order_id}...")
        
        try:
            # Get the order
            order = self.orders.get(order_id)
            
            # Check if order exists
            if order is None:
                return None
            
            # Update status to processing
            order["status"] = STATUS_PROCESSING
            
            # Validate the order items (TODO: implement validation)
            items = order.get("items", [])
            
            # Process each item
            for item in items:
                # Process the item
                processedItem = self._processItem(item)
            
            # Mark as completed
            order["status"] = STATUS_COMPLETED
            
            print(f"✅ Order processed successfully!")
            return order
            
        except Exception as e:
            # TODO: add proper error handling
            print(f"Error processing order: {e}")
            return None

    def _processItem(self, item):
        """
        This private method processes a single item.
        
        Args:
            item: The item to process
            
        Returns:
            The processed item
        """
        # Simply return the item for now (TODO: add real processing)
        return item

    def getOrderStats(self):
        """
        This method returns order statistics.
        
        Returns:
            A dictionary containing order statistics
        """
        # Initialize counters
        created_count = 0
        processing_count = 0
        completed_count = 0
        cancelled_count = 0
        
        # Loop through all orders and count by status
        for order_id, order in self.orders.items():
            # Get the status
            status = order.get("status")
            
            # Increment the appropriate counter
            if status == STATUS_CREATED:
                created_count += 1
            elif status == STATUS_PROCESSING:
                processing_count += 1
            elif status == STATUS_COMPLETED:
                completed_count += 1
            elif status == STATUS_CANCELLED:
                cancelled_count += 1
        
        # Build and return the stats dictionary
        return {
            "total": self.order_count,
            "created": created_count,
            "processing": processing_count,
            "completed": completed_count,
            "cancelled": cancelled_count,
        }


if __name__ == "__main__":
    # 🎯 Main entry point for testing
    print("🚀 Testing OrderManager...")
    
    # Create manager instance
    manager = OrderManager()
    
    # Test creating an order
    order = manager.createOrder("cust_001", [{"sku": "ITEM-1", "qty": 2}], 49.99)
    print(f"Created order: {order['id']}")
    
    # Test processing
    result = manager.processOrder(order["id"])
    print(f"✅ Done! Status: {result['status']}")
