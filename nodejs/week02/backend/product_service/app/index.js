// Import required modules
const express = require('express');
const cors = require('cors');
const pool = require('./db'); // Database connection module

const app = express();
const PORT = 8000;

// Middleware
app.use(cors());
app.use(express.json());

// Function to initialize the database table if not exists
async function initDB() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS products (
      product_id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
      stock_quantity INT NOT NULL CHECK (stock_quantity >= 0)
    );
  `);
  console.log("✅ Database initialized (products table ready)");
}

// Run database initialization at startup
initDB().catch(err => console.error("❌ DB init failed:", err));

// Health check endpoint
app.get('/', (req, res) => {
  res.send('Product service is running');
});

// CREATE product
app.post('/products/', async (req, res) => {
  const { name, description, price, stock_quantity } = req.body;
  if (!name || price === undefined || stock_quantity === undefined) {
    return res.status(422).json({ detail: 'Missing required fields' });
  }
  if (price <= 0 || stock_quantity < 0) {
    return res.status(422).json({ detail: 'Price and stock must be valid' });
  }
  try {
    const result = await pool.query(
      'INSERT INTO products (name, description, price, stock_quantity) VALUES ($1, $2, $3, $4) RETURNING *',
      [name, description, price, stock_quantity]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// READ all products
app.get('/products/', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products ORDER BY product_id');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// READ one product by ID
app.get('/products/:id', async (req, res) => {
  const id = req.params.id;
  try {
    const result = await pool.query('SELECT * FROM products WHERE product_id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ detail: 'Product not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// UPDATE product
app.put('/products/:id', async (req, res) => {
  const id = req.params.id;
  const { name, description, price, stock_quantity } = req.body;
  if (!name || price === undefined || stock_quantity === undefined) {
    return res.status(422).json({ detail: 'Missing required fields' });
  }
  if (price <= 0 || stock_quantity < 0) {
    return res.status(422).json({ detail: 'Price and stock must be valid' });
  }
  try {
    const result = await pool.query(
      'UPDATE products SET name = $1, description = $2, price = $3, stock_quantity = $4 WHERE product_id = $5 RETURNING *',
      [name, description, price, stock_quantity, id]
    );
    if (result.rows.length === 0) {
      res.status(404).json({ detail: 'Product not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

// DELETE product
app.delete('/products/:id', async (req, res) => {
  const id = req.params.id;
  try {
    const result = await pool.query(
      'DELETE FROM products WHERE product_id = $1 RETURNING *',
      [id]
    );
    if (result.rows.length === 0) {
      res.status(404).json({ detail: 'Product not found' });
    } else {
      res.json({ detail: 'Product deleted' });
    }
  } catch (err) {
    res.status(500).json({ detail: err.message });
  }
});

module.exports = app;
