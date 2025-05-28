// app/schemas.js

function validateOrderCreate(body) {
  if (!body.customer_name || !body.product_id || !body.quantity) {
    return 'Missing required fields'
  }
  if (typeof body.quantity !== 'number' || body.quantity <= 0) {
    return 'Quantity must be a positive number'
  }
  return null
}

module.exports = { validateOrderCreate }
