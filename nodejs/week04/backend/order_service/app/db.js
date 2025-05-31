// backend/product_service_nodejs/app/db.js
const { Pool } = require('pg')

const dotenv = require('dotenv');

// Load environment variables from .env file
dotenv.config();

// Use env variables or hardcode for local setup
const pool = new Pool({
    host: process.env.POSTGRES_HOST || 'localhost',
    port: process.env.POSTGRES_PORT || 5432,
    user: process.env.POSTGRES_USER || 'postgres',
    password: process.env.POSTGRES_PASSWORD || 'postgres',
    database: process.env.POSTGRES_DB || 'orders',
})

module.exports = pool
