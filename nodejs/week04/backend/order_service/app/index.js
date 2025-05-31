// nodejs-microservices/order-service/src/index.js
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const axios = require('axios');
const amqp = require('amqplib');
const dotenv = require('dotenv');

const pool = require('./db');
const { initOrderTable } = require('./models');
const { validateOrderCreate } = require('./schemas');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8001;
const PRODUCT_SERVICE_URL = process.env.PRODUCT_SERVICE_URL || 'http://product_service:8000';

app.use(cors({ origin: 'http://localhost:3000' }));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// --- RabbitMQ Connection and Event Handling ---
let channel;

async function connectRabbitMQ() {
  try {
    const connection = await amqp.connect({
      hostname: process.env.RABBITMQ_HOST,
      port: parseInt(process.env.RABBITMQ_PORT || '5672'),
      username: process.env.RABBITMQ_USER,
      password: process.env.RABBITMQ_PASS,
    });
    channel = await connection.createChannel();
    console.log('✅ Order Service connected to RabbitMQ!');

    await channel.assertExchange('order_events', 'topic', { durable: true });
    await channel.assertExchange('stock_events', 'topic', { durable: true });

    const stockDeductedQueue = 'stock_deducted_queue';
    await channel.assertQueue(stockDeductedQueue, { durable: true });
    await channel.bindQueue(stockDeductedQueue, 'stock_events', 'stock.deducted');
    await channel.bindQueue(stockDeductedQueue, 'stock_events', 'stock.failed');

    console.log('👂 Order Service waiting for stock events...');

    channel.consume(stockDeductedQueue, async (msg) => {
      if (msg !== null) {
        try {
          const stockEvent = JSON.parse(msg.content.toString());
          const orderId = stockEvent.order_id;
          const newStatus = stockEvent.status === 'success' ? 'CONFIRMED' : 'FAILED'; 
          
          console.log(`➡️ [Order Service] Received stock event for Order ID: ${orderId}, New Status: ${newStatus}`);

          const updateResult = await pool.query(
            `UPDATE orders_week04 SET status = $1, updated_at = NOW() WHERE order_id = $2 RETURNING *`,
            [newStatus, orderId]
          );

          if (updateResult.rows.length === 0) {
            console.warn(`⚠️ [Order Service] Order ID ${orderId} not found in DB for status update.`);
          } else {
            console.log(`✅ [Order Service] Order ID ${orderId} status updated to ${newStatus}.`);
          }

          channel.ack(msg);
        } catch (error) {
          console.error(`❌ [Order Service] Error processing stock event message: ${error.message}`, error);
          channel.reject(msg, false);
        }
      }
    });

  } catch (error) {
    console.error(`❌ Order Service failed to connect to RabbitMQ: ${error.message}`);
    setTimeout(connectRabbitMQ, 5000);
  }
}

async function publishOrderCreatedEvent(orderData) {
  if (!channel) {
    console.error('❌ RabbitMQ channel not available for publishing order events.');
    return;
  }
  const exchangeName = 'order_events';
  const routingKey = 'order.created';

  try {
    await channel.assertExchange(exchangeName, 'topic', { durable: true });

    channel.publish(
      exchangeName,
      routingKey,
      Buffer.from(JSON.stringify(orderData)),
      { persistent: true, contentType: 'application/json' }
    );
    console.log(`⬆️ [Order Service] Published order.created event for Order ID: ${orderData.order_id}`);
  } catch (error) {
    console.error(`❌ [Order Service] Failed to publish order.created event for Order ID ${orderData.order_id}: ${error.message}`);
  }
}

async function getProductDetails(productId) {
  try {
    const response = await axios.get(`${PRODUCT_SERVICE_URL}/products/${productId}`);
    return response.data;
  } catch (error) {
    console.error(`❌ Failed to fetch product details for ID ${productId}:`, error.message);
    return null;
  }
}

// --- CRUD Endpoints ---

app.post('/orders', async (req, res) => {
  const validationError = validateOrderCreate(req.body);
  if (validationError) {
    return res.status(422).json({ detail: validationError });
  }

  const { customer_id, items } = req.body; 

  const orderItemsForDb = items.map(item => ({
    product_id: item.product_id,
    quantity: item.quantity
  }));

  let client;
  try {
    client = await pool.connect();
    await client.query('BEGIN');

    // FIX: Ensure initial status is UPPERCASE to match DB ENUM
    const result = await client.query(
      `INSERT INTO orders_week04 (customer_id, items_json, status)
       VALUES ($1, $2, $3) RETURNING *`,
      [customer_id, JSON.stringify(orderItemsForDb), 'PENDING_STOCK_CHECK'] 
    );
    const newOrder = result.rows[0];

    await publishOrderCreatedEvent({
        order_id: newOrder.order_id,
        customer_id: newOrder.customer_id,
        items: orderItemsForDb,
        status: newOrder.status,
        created_at: newOrder.created_at
    });

    await client.query('COMMIT');
    
    res.status(202).json({
      detail: 'Order received and stock check initiated asynchronously.',
      order: newOrder
    });

  } catch (err) {
    if (client) {
      await client.query('ROLLBACK');
    }
    console.error('❌ Error creating order:', err);
    res.status(500).json({ detail: err.message || 'Internal Server Error' });
  } finally {
    if (client) {
      client.release();
    }
  }
});

app.get('/orders', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM orders_week04 ORDER BY created_at DESC');
    const orders = result.rows;

    for (const order of orders) {
      if (order.items_json) {
        order.items = JSON.parse(order.items_json); 
        delete order.items_json;

        for (const item of order.items) {
          const product = await getProductDetails(item.product_id);
          if (product) {
            item.name = product.name;
          } else {
            item.name = `Unknown Product (ID: ${item.product_id})`;
          }
        }
      } else {
        order.items = [];
      }
    }
    res.json(orders);
  } catch (err) {
    console.error('❌ Error listing orders:', err);
    res.status(500).json({ detail: err.message || 'Internal Server Error' });
  }
});

app.get('/orders/:order_id', async (req, res) => {
  const { order_id } = req.params;
  try {
    const result = await pool.query('SELECT * FROM orders_week04 WHERE order_id=$1', [order_id]);
    if (result.rows.length === 0) {
        return res.status(404).json({ detail: "Order not found" });
    }

    const order = result.rows[0];
    if (order.items_json) {
        order.items = JSON.parse(order.items_json);
        delete order.items_json;

        for (const item of order.items) {
          const product = await getProductDetails(item.product_id);
          if (product) {
            item.name = product.name;
          } else {
            item.name = `Unknown Product (ID: ${item.product_id})`;
          }
        }
      } else {
        order.items = [];
      }
    res.json(order);
  } catch (err) {
    console.error('❌ Error getting single order:', err);
    res.status(500).json({ detail: err.message || 'Internal Server Error' });
  }
});

app.get('/', (req, res) => res.send('📦 Order service is running'));

// --- Initialize and Start Server ---
async function startServer() {
  await initOrderTable();
  await connectRabbitMQ();

  app.listen(PORT, () => {
    console.log(`📦 Order service running on http://localhost:${PORT}`);
  });
}

startServer();