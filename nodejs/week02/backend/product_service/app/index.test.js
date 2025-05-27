const request = require('supertest')
const app = require('./index')
const pool = require('./db')

let createdProductIds = []

afterAll(async () => {
    // Clean up only test-created products
    for (const id of createdProductIds) {
        await pool.query('DELETE FROM products WHERE product_id = $1', [id])
    }
    await pool.end()
})

describe('Product Service API', () => {
  let createdProductId

  it('should create a product', async () => {
    const product = {
      name: 'Test Product',
      description: 'A test product',
      price: 19.99,
      stock_quantity: 5
    }
    const res = await request(app).post('/products/').send(product)
    expect(res.statusCode).toBe(201)
    expect(res.body.name).toBe('Test Product')
    createdProductId = res.body.product_id
    createdProductIds.push(createdProductId)
  })

  it('should get all products', async () => {
    const res = await request(app).get('/products/')
    expect(res.statusCode).toBe(200)
    expect(Array.isArray(res.body)).toBe(true)
    expect(res.body.length).toBeGreaterThan(0)
  })

  it('should update a product', async () => {
    const update = {
      name: 'Updated Product',
      description: 'Updated description',
      price: 29.99,
      stock_quantity: 10
    }
    const res = await request(app).put(`/products/${createdProductId}`).send(update)
    expect(res.statusCode).toBe(200)
    expect(res.body.name).toBe('Updated Product')
    expect(res.body.stock_quantity).toBe(10)
  })

  it('should return 404 for missing product', async () => {
    const res = await request(app).get('/products/999999')
    expect(res.statusCode).toBe(404)
  })

  it('should reject invalid price', async () => {
    const product = {
      name: 'Invalid Price',
      description: '',
      price: -10,
      stock_quantity: 2
    }
    const res = await request(app).post('/products/').send(product)
    expect(res.statusCode).toBe(422)
  })

  it('should delete the product', async () => {
    const res = await request(app).delete(`/products/${createdProductId}`)
    expect(res.statusCode).toBe(200)
    expect(res.body.detail).toBe('Product deleted')
    // Remove from cleanup list since it's already deleted
    createdProductIds = createdProductIds.filter(id => id !== createdProductId)
  })
})