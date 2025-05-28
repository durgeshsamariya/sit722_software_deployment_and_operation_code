// app/models.js
const pool = require('./db');

async function initOrderTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS orders_week03 (
        order_id SERIAL PRIMARY KEY,
        customer_name VARCHAR(255) NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `);
  console.log("✅ orders_week03 table ensured");
}

module.exports = { initOrderTable };
