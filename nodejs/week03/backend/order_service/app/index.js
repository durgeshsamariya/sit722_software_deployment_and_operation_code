// index.js
const express = require('express');
const cors = require('cors');
const pool = require('./db');

const app = express();
app.use(cors());
app.use(express.json());

// Initialize table on startup
(async () => {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS orders (
      id SERIAL PRIMARY KEY,
      customer_name TEXT NOT NULL,
      item TEXT NOT NULL
    );
  `);
  console.log('✅ Order table ensured');
})().catch(err => console.error('❌ Error creating order table', err));

// CRUD endpoints

app.get('/orders', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM orders;');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/orders/:id', async (req, res) => {
  try {
    const { rows } = await pool.query(
      'SELECT * FROM orders WHERE id = $1;',
      [req.params.id]
    );
    if (!rows.length) return res.status(404).json({ error: 'Not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/orders', async (req, res) => {
  const { customer_name, item } = req.body;
  try {
    const { rows } = await pool.query(
      'INSERT INTO orders (customer_name, item) VALUES ($1, $2) RETURNING *;',
      [customer_name, item]
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/orders/:id', async (req, res) => {
  const { customer_name, item } = req.body;
  try {
    const { rows } = await pool.query(
      'UPDATE orders SET customer_name = $1, item = $2 WHERE id = $3 RETURNING *;',
      [customer_name, item, req.params.id]
    );
    if (!rows.length) return res.status(404).json({ error: 'Not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/orders/:id', async (req, res) => {
  try {
    const { rowCount } = await pool.query(
      'DELETE FROM orders WHERE id = $1;',
      [req.params.id]
    );
    if (!rowCount) return res.status(404).json({ error: 'Not found' });
    res.status(204).send();
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = 4001;
app.listen(PORT, () => {
  console.log(`📦 Order service running on http://localhost:${PORT}`);
});
