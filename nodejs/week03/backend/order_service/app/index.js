// index.js
const express = require('express');
const cors = require('cors');
const pool = require('./db');
const { initOrderTable } = require('./models');
const { validateOrderCreate} = require('./schemas');
const axios = require('axios');

// Load environment variables from .env file
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8001
const PRODUCT_SERVICE_URL = process.env.PRODUCT_SERVICE_URL || 'http://localhost:8000';

app.use(cors());
app.use(express.json());

// Ensure table exists
initOrderTable().catch(err => console.error("DB init failed:", err));

// ---- Utility: Adjust product stock via Product Service ----
async function adjustProductStock(product_id, delta) {
  // 1. Get product info
  const prodResp = await axios.get(`${PRODUCT_SERVICE_URL}/products/${product_id}`)
    .catch(() => null)
  console.log("Adusting stock for product_id:", product_id, "by delta:", delta);
  if (!prodResp || prodResp.status !== 200) {
    const err = new Error("Product not found in Product Service")
    err.status = 404
    throw err
  }
  const product = prodResp.data
  const newStock = product.stock_quantity + delta
  if (newStock < 0) {
    const err = new Error("Not enough stock for update")
    err.status = 400
    throw err
  }
  // 2. Update stock
  const updateResp = await axios.put(`${PRODUCT_SERVICE_URL}/products/${product_id}/stock`, null, {
    params: { stock_quantity: newStock }
  })
  if (![200, 201].includes(updateResp.status)) {
    const err = new Error("Failed to update stock in Product Service")
    err.status = updateResp.status
    throw err
  }
}

// CRUD endpoints

// Create order
app.post('/orders/', async (req, res) => {
  const { product_id, customer_name, quantity } = req.body
  try {
    await adjustProductStock(product_id, -quantity)
    const result = await pool.query(
      `INSERT INTO orders_week03 (product_id, customer_name, quantity)
       VALUES ($1, $2, $3) RETURNING *`,
      [product_id, customer_name, quantity]
    )
    res.status(201).json(result.rows[0])
  } catch (err) {
    res.status(err.status || 500).json({ detail: err.message })
  }
})

// List all orders
app.get('/orders/', async (req, res) => {
  const result = await pool.query('SELECT * FROM orders_week03')
  res.json(result.rows)
})

// Get one order
app.get('/orders/:order_id', async (req, res) => {
  const { order_id } = req.params
  const result = await pool.query('SELECT * FROM orders_week03 WHERE order_id=$1', [order_id])
  if (!result.rows.length) return res.status(404).json({ detail: "Order not found" })
  res.json(result.rows[0])
})

// Update order (with stock adjustment)
app.put('/orders/:order_id', async (req, res) => {
  const { order_id } = req.params
  const { quantity, customer_name } = req.body

  // Fetch order to get prev_qty and product_id
  const orderResult = await pool.query('SELECT * FROM orders_week03 WHERE order_id=$1', [order_id])
  if (!orderResult.rows.length) return res.status(404).json({ detail: "Order not found" })
  const order = orderResult.rows[0]

  const delta = quantity - order.quantity
  try {
    await adjustProductStock(order.product_id, -delta)
    const upd = await pool.query(
      `UPDATE orders_week03
       SET quantity=$1, customer_name=$2
       WHERE order_id=$3 RETURNING *`,
      [quantity, customer_name || order.customer_name, order_id]
    )
    res.json(upd.rows[0])
  } catch (err) {
    res.status(err.status || 500).json({ detail: err.message })
  }
})

// Delete order (return stock)
app.delete('/orders/:order_id', async (req, res) => {
  const { order_id } = req.params
  // Get the order
  const orderResult = await pool.query('SELECT * FROM orders_week03 WHERE order_id=$1', [order_id])
  if (!orderResult.rows.length) return res.status(404).json({ detail: "Order not found" })
  const order = orderResult.rows[0]
  try {
    await adjustProductStock(order.product_id, order.quantity)
    await pool.query('DELETE FROM orders_week03 WHERE order_id=$1', [order_id])
    res.status(204).end()
  } catch (err) {
    res.status(err.status || 500).json({ detail: err.message })
  }
})

// ---- Start server ----
app.listen(PORT, () => {
  console.log(`📦 Order service running on http://localhost:${PORT}`);
});
