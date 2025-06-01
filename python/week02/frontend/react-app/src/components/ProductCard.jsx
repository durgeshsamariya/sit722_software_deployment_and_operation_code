// /components/ProductCard.jsx

import React from 'react';
import Button from './Button'; // Import the reusable Button component

function ProductCard({ product, onEdit, onDelete }) {
  return (
    <div className="product-card">
      <div>
        <h3>{product.name}</h3>
        <p className="product-card-description">
          {product.description || 'No description provided.'}
        </p>
        <div className="product-card-price">
          ${Number(product.price).toFixed(2)}
        </div>
        <div className="product-card-stock">
          Stock: {product.stock_quantity}
        </div>
      </div>
      <div className="product-card-actions">
        <Button variant="primary" onClick={() => onEdit(product)}>
          Edit
        </Button>
        <Button variant="danger" onClick={() => onDelete(product.product_id)}>
          Delete
        </Button>
      </div>
    </div>
  );
}

export default ProductCard;