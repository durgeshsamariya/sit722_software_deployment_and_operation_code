const express = require('express');
const cors = require('cors');
const pool = require('./db'); // Use the db.js module

const app = express();
const PORT = 4000;
app.use(cors());
app.use(express.json());

async function initDB() {
    await pool.query(`
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price NUMERIC
        );
    `);
    console.log("✅ Database initialized");
}

initDB().catch(err => console.error("❌ DB init failed:", err));

// Health check
app.get('/', (req, res) => {
  res.send('Product service is running');
});

// Create product
app.post('/products', async (req, res) => {
  const { name, price } = req.body;
  try {
    const result = await pool.query(
      'INSERT INTO products (name, price) VALUES ($1, $2) RETURNING *',
      [name, price]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get all products
app.get('/products', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get product by ID
app.get('/products/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const result = await pool.query('SELECT * FROM products WHERE id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update product
app.put('/products/:id', async (req, res) => {
  const { id } = req.params;
  const { name, price } = req.body;
  try {
    const result = await pool.query(
      'UPDATE products SET name = $1, price = $2 WHERE id = $3 RETURNING *',
      [name, price, id]
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' });
    } else {
      res.json(result.rows[0]);
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete product
app.delete('/products/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const result = await pool.query('DELETE FROM products WHERE id = $1 RETURNING *', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' });
    } else {
      res.json({ message: 'Product deleted' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Product service running on port ${PORT}`);
});
