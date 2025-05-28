// app/index.js
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const pool = require('./db');
const { initProductTable } = require('./models');
const { uploadToAzure } = require('./azure');

const app = express();
const PORT = 8000;
const upload = multer();

app.use(cors());
app.use(express.json());

// Ensure table exists
initProductTable().catch(err => console.error("DB init failed:", err));

// --------- CRUD Endpoints ---------

// Create Product (with optional image)
app.post('/products', upload.single('image'), async (req, res) => {
  const { name, description, price, stock_quantity } = req.body;
  let image_url = null;
  try {
    if (req.file) {
      image_url = await uploadToAzure(req.file.buffer, req.file.originalname, req.file.mimetype);
    }
    const result = await pool.query(
      `INSERT INTO products_week03 (name, description, price, stock_quantity, image_url) 
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [name, description, price, stock_quantity, image_url]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Read All Products
app.get('/products', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products_week03 ORDER BY created_at DESC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Read One Product
app.get('/products/:id', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products_week03 WHERE product_id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Product (optionally update image)
app.put('/products/:id', upload.single('image'), async (req, res) => {
  const { name, description, price, stock_quantity } = req.body;
  let image_url = null;
  try {
    // Only upload new image if provided
    if (req.file) {
      image_url = await uploadToAzure(req.file.buffer, req.file.originalname, req.file.mimetype);
    }
    // Build dynamic query
    const updates = [];
    const values = [];
    if (name) { updates.push('name = $' + (values.length + 1)); values.push(name); }
    if (description) { updates.push('description = $' + (values.length + 1)); values.push(description); }
    if (price) { updates.push('price = $' + (values.length + 1)); values.push(price); }
    if (stock_quantity) { updates.push('stock_quantity = $' + (values.length + 1)); values.push(stock_quantity); }
    if (image_url) { updates.push('image_url = $' + (values.length + 1)); values.push(image_url); }
    if (updates.length === 0) return res.status(400).json({ error: "No fields to update" });

    const query = `
      UPDATE products_week03 
      SET ${updates.join(', ')}, updated_at = NOW() 
      WHERE product_id = $${values.length + 1}
      RETURNING *;
    `;
    values.push(req.params.id);
    const result = await pool.query(query, values);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete Product
app.delete('/products/:id', async (req, res) => {
  try {
    const result = await pool.query('DELETE FROM products_week03 WHERE product_id = $1 RETURNING *', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json({ detail: 'Product deleted successfully' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update Stock
app.put('/products/:id/stock', async (req, res) => {
  const stock_quantity = parseInt(req.query.stock_quantity);
  if (isNaN(stock_quantity) || stock_quantity < 0) {
    return res.status(400).json({ error: 'Invalid stock_quantity' });
  }
  try {
    const result = await pool.query(
      'UPDATE products_week03 SET stock_quantity = $1, updated_at = NOW() WHERE product_id = $2 RETURNING *',
      [stock_quantity, req.params.id]
    );
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Health check
app.get('/', (req, res) => res.send('Product service is running'));

// Start server
app.listen(PORT, () => console.log(`Product service running on port ${PORT}`));

module.exports = app;
