// db.js
const { Pool } = require('pg');

const pool = new Pool({
    host: 'order_db',
    port: 5432,
    user: 'postgres',
    password: 'postgres',
    database: 'orders'
});

module.exports = pool;
