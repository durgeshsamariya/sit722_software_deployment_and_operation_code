// app/models.js (Order Service)
const pool = require('./db');

// In nodejs-microservices/order-service/src/models.js
async function initOrderTable() {
    try {

      await pool.query(`
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
                    CREATE TYPE orderstatus AS ENUM (
                        'PENDING_STOCK_CHECK',
                        'CONFIRMED',
                        'CANCELLED',
                        'FAILED'
                    );
                END IF;
            END $$;
        `);
        console.log("✅ orderstatus ENUM type ensured");

        await pool.query(`
            CREATE TABLE IF NOT EXISTS orders_week04 (
                order_id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                status orderstatus NOT NULL,
                items_json JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        `);
        console.log("✅ orders_week04 table ensured");
    } catch (error) {
        console.error('❌ Error initializing order table:', error);
        throw error;
    }
}

module.exports = { initOrderTable };