// app/schemas.js (Order Service)

function validateOrderCreate(body) {
  if (!body.customer_id) {
    return 'Customer ID is required.';
  }
  if (!Array.isArray(body.items) || body.items.length === 0) {
    return 'Order must contain at least one item.';
  }

  for (const item of body.items) {
    if (!item.product_id || typeof item.quantity !== 'number' || item.quantity <= 0) {
      return 'Each item must have a valid product_id and a positive quantity.';
    }
  }
  return null; // No validation errors
}

module.exports = { validateOrderCreate };