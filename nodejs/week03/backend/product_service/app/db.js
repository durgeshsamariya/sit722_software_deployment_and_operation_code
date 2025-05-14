// db.js
const { Pool } = require('pg');

const pool = new Pool({
    host: 'product_db',       // matches docker-compose service name
    port: 5432,
    user: 'postgres',
    password: 'postgres',
    database: 'products'
});

module.exports = pool;
