// Import required modules
const express = require('express');
const cors = require('cors');
const pool = require('./db'); // Database connection module

// Initialize Express app and define the port
const app = express();
const PORT = 4000;

// Middleware setup
app.use(cors()); // Enable Cross-Origin Resource Sharing
app.use(express.json()); // Parse incoming JSON requests

// Function to initialize the database
async function initDB() {
    await pool.query(`
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,       -- Unique identifier for each product
            name TEXT NOT NULL,          -- Name of the product (required)
            description TEXT,            -- Optional description of the product
            price NUMERIC                -- Price of the product
        );
    `);
    console.log("✅ Database initialized");
}

// Initialize the database and handle errors
initDB().catch(err => console.error("❌ DB init failed:", err));

// Health check endpoint
app.get('/', (req, res) => {
  res.send('Product service is running'); // Simple response to confirm service is running
});

// Endpoint to create a new product
app.post('/products', async (req, res) => {
  const { name, price } = req.body; // Extract product details from request body
  try {
    const result = await pool.query(
      'INSERT INTO products (name, price) VALUES ($1, $2) RETURNING *',
      [name, price]
    );
    res.status(201).json(result.rows[0]); // Return the created product
  } catch (err) {
    res.status(500).json({ error: err.message }); // Handle errors
  }
});

// Endpoint to retrieve all products
app.get('/products', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products'); // Fetch all products
    res.json(result.rows); // Return the list of products
  } catch (err) {
    res.status(500).json({ error: err.message }); // Handle errors
  }
});

// Endpoint to retrieve a product by ID
app.get('/products/:id', async (req, res) => {
  const { id } = req.params; // Extract product ID from request parameters
  try {
    const result = await pool.query('SELECT * FROM products WHERE id = $1', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' }); // Handle case where product is not found
    } else {
      res.json(result.rows[0]); // Return the product
    }
  } catch (err) {
    res.status(500).json({ error: err.message }); // Handle errors
  }
});

// Endpoint to update a product by ID
app.put('/products/:id', async (req, res) => {
  const { id } = req.params; // Extract product ID from request parameters
  const { name, price } = req.body; // Extract updated product details from request body
  try {
    const result = await pool.query(
      'UPDATE products SET name = $1, price = $2 WHERE id = $3 RETURNING *',
      [name, price, id]
    );
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' }); // Handle case where product is not found
    } else {
      res.json(result.rows[0]); // Return the updated product
    }
  } catch (err) {
    res.status(500).json({ error: err.message }); // Handle errors
  }
});

// Endpoint to delete a product by ID
app.delete('/products/:id', async (req, res) => {
  const { id } = req.params; // Extract product ID from request parameters
  try {
    const result = await pool.query('DELETE FROM products WHERE id = $1 RETURNING *', [id]);
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Product not found' }); // Handle case where product is not found
    } else {
      res.json({ message: 'Product deleted' }); // Confirm deletion
    }
  } catch (err) {
    res.status(500).json({ error: err.message }); // Handle errors
  }
});

// Start the server and listen on the specified port
app.listen(PORT, () => {
  console.log(`Product service running on port ${PORT}`);
});
