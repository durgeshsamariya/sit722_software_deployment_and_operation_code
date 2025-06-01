// /src/components/OrderList.jsx

import React from 'react';
import OrderRow from './OrderRow'; 

function OrderList({ orders, onEdit, onDelete, PRODUCT_API_BASE_URL }) { // Added PRODUCT_API_BASE_URL prop
  if (!orders || orders.length === 0) {
    return <p className="status-message">No orders found. Create one to get started!</p>;
  }

  return (
    <div className="order-list-container">
      <h2>Current Orders</h2>
      <table className="order-table">
        <thead>
          <tr>
            <th>Order ID</th> {/* This column will also contain the expand toggle */}
            <th>Product ID</th>
            <th>Quantity</th>
            <th>Customer Name</th>
            <th>Created At</th>
            <th>Updated At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {/* Map over the orders array to render an OrderRow for each order */}
          {orders.map((order) => (
            <OrderRow
              key={order.order_id} // Unique key for each row
              order={order} // Pass the individual order object
              onEdit={onEdit} // Pass the edit handler
              onDelete={onDelete} // Pass the delete handler
              PRODUCT_API_BASE_URL={PRODUCT_API_BASE_URL} // Pass the product API URL
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default OrderList;