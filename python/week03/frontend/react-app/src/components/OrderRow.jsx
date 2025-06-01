// /src/components/OrderRow.jsx

import React, { useState, useEffect } from 'react';
import Button from './Button'; // Reusable Button component

// OrderRow component responsible for a single order row and its expandable product details
function OrderRow({ order, onEdit, onDelete, PRODUCT_API_BASE_URL }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [productDetails, setProductDetails] = useState(null);
  const [isProductLoading, setIsProductLoading] = useState(false);
  const [productError, setProductError] = useState(null);

  // Effect to fetch product details when the row expands
  useEffect(() => {
    // Only fetch if expanded, details aren't already loaded, and not currently loading
    if (isExpanded && !productDetails && !isProductLoading) {
      const fetchProductDetails = async () => {
        setIsProductLoading(true);
        setProductError(null); // Clear any previous errors
        try {
          const response = await fetch(`${PRODUCT_API_BASE_URL}/products/${order.product_id}`);
          if (!response.ok) {
            throw new Error(`Failed to fetch product details: ${response.status}`);
          }
          const data = await response.json();
          setProductDetails(data); // Store fetched product details
        } catch (error) {
          console.error(`Error fetching product details for ID ${order.product_id}:`, error);
          setProductError("Could not load product details."); // Set user-friendly error message
        } finally {
          setIsProductLoading(false); // End loading state
        }
      };

      fetchProductDetails();
    }
  }, [isExpanded, order.product_id, productDetails, isProductLoading, PRODUCT_API_BASE_URL]); // Dependencies for useEffect

  // Toggles the expanded state of the row
  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <>
      {/* Main Order Row */}
      <tr>
        <td>
          {/* Expand/Collapse Button */}
          <Button variant="secondary" onClick={toggleExpand} className="toggle-button">
            {isExpanded ? '-' : '+'} {/* Change text based on expanded state */}
          </Button>
          {order.order_id}
        </td>
        <td>{order.product_id}</td>
        <td>{order.quantity}</td>
        <td>{order.customer_name}</td>
        <td>{new Date(order.created_at).toLocaleString()}</td> {/* Formatted creation timestamp */}
        <td>{order.updated_at ? new Date(order.updated_at).toLocaleString() : 'N/A'}</td> {/* Formatted update timestamp */}
        <td className="order-actions">
          <Button variant="primary" onClick={() => onEdit(order)}>
            Edit
          </Button>
          <Button variant="danger" onClick={() => onDelete(order.order_id)}>
            Delete
          </Button>
        </td>
      </tr>

      {/* Child Row for Product Details (conditionally rendered when isExpanded is true) */}
      {isExpanded && (
        <tr className="product-detail-row">
          <td colSpan="7"> {/* This cell spans across all 7 columns of the parent table */}
            <div className="product-detail-card">
              {/* Conditional rendering for loading, error, or product details */}
              {isProductLoading && <p className="status-message loading">Loading product details...</p>}
              {productError && <p className="status-message error">{productError}</p>}
              {productDetails && (
                <>
                  <h4>Product Details:</h4>
                  <p><strong>Name:</strong> {productDetails.name}</p>
                  <p><strong>Description:</strong> {productDetails.description || 'N/A'}</p>
                  <p><strong>Price:</strong> ${Number(productDetails.price).toFixed(2)}</p>
                  <p><strong>Stock:</strong> {productDetails.stock_quantity}</p>
                </>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default OrderRow;