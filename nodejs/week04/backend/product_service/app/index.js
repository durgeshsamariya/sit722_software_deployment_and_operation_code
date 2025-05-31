// app/index.js (Product Service)
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const pool = require('./db');
const { initProductTable } = require('./models');
const { uploadToAzure } = require('./azure');
const amqp = require('amqplib'); // NEW: RabbitMQ library
const dotenv = require('dotenv'); // NEW: For RabbitMQ env vars

dotenv.config(); // Load environment variables (ensure this is at the top)

const app = express();
const PORT = process.env.PORT || 8000; // Use env PORT
const upload = multer();

app.use(cors({ origin: 'http://localhost:3000' })); // Explicitly allow frontend origin
app.use(express.json());
app.use(express.urlencoded({ extended: true })); // For parsing URL-encoded bodies

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
    console.log('✅ Product Service connected to RabbitMQ!');

    // Declare exchanges (ensure they exist for both producer/consumer roles)
    await channel.assertExchange('order_events', 'topic', { durable: true });
    await channel.assertExchange('stock_events', 'topic', { durable: true });

    // Consumer setup: Listen for order.created events
    const orderCreatedQueue = 'order_created_queue'; // Consistent with Python service
    await channel.assertQueue(orderCreatedQueue, { durable: true });
    await channel.bindQueue(orderCreatedQueue, 'order_events', 'order.created');

    console.log('👂 Product Service waiting for order.created messages...');

    channel.consume(orderCreatedQueue, async (msg) => {
      if (msg !== null) {
        try {
          const orderData = JSON.parse(msg.content.toString());
          console.log(`➡️ [Product Service] Received order.created event for Order ID: ${orderData.order_id}`);

          let allItemsConfirmed = true;
          const processedItems = [];

          for (const item of orderData.items) {
            const { product_id, quantity } = item;
            let transactionClient; // Use a client for transaction

            try {
                transactionClient = await pool.connect(); // Get a client from the pool
                await transactionClient.query('BEGIN'); // Start transaction

                // Check current stock
                const productQueryResult = await transactionClient.query(
                    'SELECT stock_quantity FROM products_week03 WHERE product_id = $1 FOR UPDATE', // FOR UPDATE to lock row
                    [product_id]
                );
                const product = productQueryResult.rows[0];

                if (!product || product.stock_quantity < quantity) {
                    allItemsConfirmed = false;
                    console.warn(`⚠️ [Product Service] Insufficient stock or product not found for product_id: ${product_id} in Order ID: ${orderData.order_id}`);
                    processedItems.push({ product_id, quantity, status: 'failed', message: 'Insufficient stock or product not found' });
                    await transactionClient.query('ROLLBACK'); // Rollback if condition not met
                } else {
                    // Deduct stock
                    const deductResult = await transactionClient.query(
                        'UPDATE products_week03 SET stock_quantity = stock_quantity - $1 WHERE product_id = $2 RETURNING product_id, stock_quantity',
                        [quantity, product_id]
                    );

                    if (deductResult.rows[0]) {
                        console.log(`✅ [Product Service] Deducted ${quantity} from product ${product_id} for Order ID: ${orderData.order_id}. New stock: ${deductResult.rows[0].stock_quantity}`);
                        processedItems.push({ product_id, quantity, status: 'deducted', message: 'Stock deducted successfully' });
                        await transactionClient.query('COMMIT'); // Commit transaction
                    } else {
                        // This case should ideally not happen if FOR UPDATE and stock check passed
                        allItemsConfirmed = false;
                        processedItems.push({ product_id, quantity, status: 'failed', message: 'Failed to deduct stock due to unknown issue' });
                        console.error(`❌ [Product Service] Unexpected failure to deduct stock for product ${product_id} in Order ID: ${orderData.order_id}`);
                        await transactionClient.query('ROLLBACK'); // Rollback
                    }
                }
            } catch (txError) {
                console.error(`❌ [Product Service] Transaction error for product ${product_id} in Order ID ${orderData.order_id}: ${txError.message}`, txError);
                allItemsConfirmed = false;
                processedItems.push({ product_id, quantity, status: 'failed', message: `Internal error during stock deduction: ${txError.message}` });
                if (transactionClient) {
                    await transactionClient.query('ROLLBACK'); // Ensure rollback on any error
                }
            } finally {
                if (transactionClient) {
                    transactionClient.release(); // Release the client back to the pool
                }
            }
          } // End of for loop for items

          const overallStatus = allItemsConfirmed ? 'success' : 'failed';
          const overallMessage = allItemsConfirmed ? 'Stock deducted for all items' : 'Stock deduction failed for some items';

          // Publish stock event back to Order Service
          await publishStockEvent(
            orderData.order_id,
            processedItems, // Send individual item statuses
            overallStatus,
            overallMessage
          );

          channel.ack(msg); // Acknowledge message after processing
        } catch (error) {
          console.error(`❌ [Product Service] Error processing order.created message for Order ID ${JSON.parse(msg.content.toString()).order_id}: ${error.message}`, error);
          channel.reject(msg, false); // Reject message (false = don't requeue if it's a persistent error)
        }
      }
    });

  } catch (error) {
    console.error(`❌ Product Service failed to connect to RabbitMQ: ${error.message}`);
    // Implement robust retry logic in production
    setTimeout(connectRabbitMQ, 5000); // Retry connection after 5 seconds
  }
}

async function publishStockEvent(orderId, items, status, message) {
  if (!channel) {
    console.error('❌ RabbitMQ channel not available for publishing stock events.');
    return;
  }
  const eventData = {
    order_id: orderId,
    items: items, // Contains product_id, quantity, status, message for each item
    status: status, // "success" or "failed" (overall status)
    message: message,
    timestamp: new Date().toISOString(), // ISO 8601 format
  };
  const routingKey = status === 'success' ? 'stock.deducted' : 'stock.failed';

  try {
    const exchangeName = 'stock_events';
    // Ensure the exchange exists
    await channel.assertExchange(exchangeName, 'topic', { durable: true });

    channel.publish(
      exchangeName,
      routingKey,
      Buffer.from(JSON.stringify(eventData)),
      { persistent: true, contentType: 'application/json' }
    );
    console.log(`⬆️ [Product Service] Published stock event for Order ID: ${orderId}, Status: ${status} (Routing Key: ${routingKey})`);
  } catch (error) {
    console.error(`❌ [Product Service] Failed to publish stock event for Order ID ${orderId}: ${error.message}`);
  }
}

// --- CRUD Endpoints ---

// Create Product (with optional image)
app.post('/products', upload.single('image'), async (req, res) => {
  const { name, description, price, stock_quantity } = req.body;
  let image_url = null;

  // Basic validation (can be enhanced with a validation library)
  if (!name || !price || isNaN(parseFloat(price)) || !stock_quantity || isNaN(parseInt(stock_quantity))) {
    return res.status(400).json({ error: 'Name, valid price, and valid stock_quantity are required.' });
  }
  if (parseInt(stock_quantity) < 0) {
    return res.status(400).json({ error: 'Stock quantity cannot be negative.' });
  }

  try {
    if (req.file) {
      image_url = await uploadToAzure(req.file.buffer, req.file.originalname, req.file.mimetype);
    }
    const result = await pool.query(
      `INSERT INTO products_week03 (name, description, price, stock_quantity, image_url) 
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [name, description, price, stock_quantity, image_url]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    console.error('Error creating product:', err);
    res.status(500).json({ error: err.message || 'Internal Server Error' });
  }
});

// Read All Products
app.get('/products', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products_week03 ORDER BY created_at DESC');
    res.json(result.rows);
  } catch (err) {
    console.error('Error fetching products:', err);
    res.status(500).json({ error: err.message || 'Internal Server Error' });
  }
});

// Read One Product
app.get('/products/:id', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products_week03 WHERE product_id = $1', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Error fetching product by ID:', err);
    res.status(500).json({ error: err.message || 'Internal Server Error' });
  }
});

// Update Product (optionally update image)
app.put('/products/:id', upload.single('image'), async (req, res) => {
  const { name, description, price, stock_quantity } = req.body;
  let image_url = null;

  // Basic validation
  if (!name && !description && !price && !stock_quantity && !req.file) {
    return res.status(400).json({ error: 'No fields to update.' });
  }

  const updates = [];
  const values = [];
  let paramCounter = 1;

  if (name !== undefined) { updates.push(`name = $${paramCounter}`); values.push(name); paramCounter++; }
  if (description !== undefined) { updates.push(`description = $${paramCounter}`); values.push(description); paramCounter++; }
  if (price !== undefined) {
    const parsedPrice = parseFloat(price);
    if (isNaN(parsedPrice) || parsedPrice < 0) return res.status(400).json({ error: 'Invalid price.' });
    updates.push(`price = $${paramCounter}`); values.push(parsedPrice); paramCounter++;
  }
  if (stock_quantity !== undefined) {
    const parsedStock = parseInt(stock_quantity);
    if (isNaN(parsedStock) || parsedStock < 0) return res.status(400).json({ error: 'Invalid stock quantity.' });
    updates.push(`stock_quantity = $${paramCounter}`); values.push(parsedStock); paramCounter++;
  }

  try {
    if (req.file) {
      image_url = await uploadToAzure(req.file.buffer, req.file.originalname, req.file.mimetype);
      updates.push(`image_url = $${paramCounter}`); values.push(image_url); paramCounter++;
    }

    if (updates.length === 0) { // Should be caught by earlier validation but good to have
        return res.status(400).json({ error: "No valid fields to update" });
    }

    const query = `
      UPDATE products_week03 
      SET ${updates.join(', ')}, updated_at = NOW() 
      WHERE product_id = $${paramCounter}
      RETURNING *;
    `;
    values.push(req.params.id); // Add product_id last

    const result = await pool.query(query, values);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.json(result.rows[0]);
  } catch (err) {
    console.error('Error updating product:', err);
    res.status(500).json({ error: err.message || 'Internal Server Error' });
  }
});

// Delete Product
app.delete('/products/:id', async (req, res) => {
  try {
    const result = await pool.query('DELETE FROM products_week03 WHERE product_id = $1 RETURNING *', [req.params.id]);
    if (result.rows.length === 0) return res.status(404).json({ error: 'Product not found' });
    res.status(204).send(); // 204 No Content for successful deletion
  } catch (err) {
    console.error('Error deleting product:', err);
    res.status(500).json({ error: err.message || 'Internal Server Error' });
  }
});

// REMOVED: Direct Update Stock endpoint
// The stock update is now handled asynchronously via RabbitMQ consumer for order events.
// The /products/:id/stock endpoint is no longer directly invoked by the Order Service.

// Health check
app.get('/', (req, res) => res.send('Product service is running'));

// --- Initialize and Start Server ---
async function startServer() {
  await initProductTable(); // Ensure table exists
  await connectRabbitMQ(); // Connect to RabbitMQ

  app.listen(PORT, () => {
    console.log(`Product Service running on port ${PORT}`);
  });
}

startServer();
