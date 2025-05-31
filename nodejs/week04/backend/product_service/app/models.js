// app/models.js
const pool = require('./db');

async function initProductTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS products_week03 (
      product_id SERIAL PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      description TEXT,
      price NUMERIC(10,2) NOT NULL,
      stock_quantity INT NOT NULL DEFAULT 0,
      image_url TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ
    );
  `);
  console.log("✅ products_week03 table ensured");
}

module.exports = { initProductTable };
