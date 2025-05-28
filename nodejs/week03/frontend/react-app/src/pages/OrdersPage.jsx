import { useEffect, useState } from 'react'

export default function OrdersPage() {
  const [orders, setOrders] = useState([])
  const [products, setProducts] = useState([])
  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderForm, setOrderForm] = useState({
    customer_name: '',
    product_id: '',
    quantity: '',
  })
  const [orderErrors, setOrderErrors] = useState({})
  const [orderEditId, setOrderEditId] = useState(null)

  // Fetch orders and products
  const fetchOrders = () => {
    fetch('http://localhost:8001/orders/')
      .then((res) => res.json())
      .then((data) => setOrders(data))
      .catch(() => setOrders([]))
  }

  const fetchProducts = () => {
    fetch('http://localhost:8000/products/')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setProducts([]))
  }

  useEffect(() => {
    fetchOrders()
    fetchProducts()
  }, [])

  // Order Handlers
  const handleOrderOpenForm = () => {
    setOrderForm({ customer_name: '', product_id: '', quantity: '' })
    setOrderErrors({})
    setOrderEditId(null)
    setShowOrderForm(true)
  }

  const handleOrderEdit = (order) => {
    setOrderForm({
      customer_name: order.customer_name,
      product_id: order.product_id,
      quantity: order.quantity,
    })
    setOrderErrors({})
    setOrderEditId(order.order_id)
    setShowOrderForm(true)
  }

  const handleOrderCloseForm = () => {
    setShowOrderForm(false)
    setOrderEditId(null)
  }

  const handleOrderDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this order?')) return
    await fetch(`http://localhost:8001/orders/${id}`, { method: 'DELETE' })
    fetchOrders()
    fetchProducts() // Update stock after deletion
  }

  const handleOrderChange = (e) => {
    setOrderForm({ ...orderForm, [e.target.name]: e.target.value })
  }

  const handleOrderSubmit = async (e) => {
    e.preventDefault()
    setOrderErrors({})
    const payload = {
      customer_name: orderForm.customer_name,
      product_id: Number(orderForm.product_id),
      quantity: Number(orderForm.quantity)
    }
    try {
      let res
      if (orderEditId) {
        res = await fetch(`http://localhost:8001/orders/${orderEditId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
      } else {
        res = await fetch('http://localhost:8001/orders/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
      }
      if (res.status === 201 || res.status === 200) {
        setShowOrderForm(false)
        setOrderEditId(null)
        fetchOrders()
        fetchProducts()
      } else if (res.status === 422) {
        const errorData = await res.json()
        const fieldErrors = {}
        if (errorData && errorData.detail) {
          for (const err of errorData.detail) {
            const loc = err.loc[err.loc.length - 1]
            fieldErrors[loc] = err.msg
          }
        }
        setOrderErrors(fieldErrors)
      }
    } catch {}
  }

  // UI
  return (
    <div>
      <button
        style={{
          background: '#2979ff',
          color: 'white',
          padding: '8px 16px',
          border: 'none',
          borderRadius: 4,
          fontWeight: 'bold',
          marginBottom: 16,
          cursor: 'pointer',
        }}
        onClick={handleOrderOpenForm}
      >
        Add Order
      </button>

      {showOrderForm && (
        <div
          style={{
            border: '1px solid #eee',
            borderRadius: 8,
            padding: 25,
            marginBottom: 32,
            maxWidth: '100vw',
            width: 500,
            background: '#f9f9f9',
          }}
        >
          <h2 style={{ color: 'black' }}>{orderEditId ? 'Edit Order' : 'Add New Order'}</h2>
          <form onSubmit={handleOrderSubmit} autoComplete="off" style={{ color: 'black', padding: 10 }}>
            <div style={{ marginBottom: 16, color: 'black' }}>
              <label>
                Customer Name:
                <input
                  type="text"
                  name="customer_name"
                  value={orderForm.customer_name}
                  onChange={handleOrderChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  required
                />
              </label>
              {orderErrors.customer_name && (
                <div style={{ color: 'red', fontSize: 12 }}>{orderErrors.customer_name}</div>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>
                Product:
                <select
                  name="product_id"
                  value={orderForm.product_id}
                  onChange={handleOrderChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  required
                >
                  <option value="">Select product...</option>
                  {products.map((prod) => (
                    <option key={prod.product_id} value={prod.product_id}>
                      {prod.name}
                    </option>
                  ))}
                </select>
              </label>
              {orderErrors.product_id && (
                <div style={{ color: 'red', fontSize: 12 }}>{orderErrors.product_id}</div>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>
                Quantity:
                <input
                  type="number"
                  name="quantity"
                  value={orderForm.quantity}
                  onChange={handleOrderChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  min="1"
                  required
                />
              </label>
              {orderErrors.quantity && (
                <div style={{ color: 'red', fontSize: 12 }}>{orderErrors.quantity}</div>
              )}
            </div>
            <button
              type="submit"
              style={{
                background: '#2979ff',
                color: 'white',
                padding: '8px 16px',
                border: 'none',
                borderRadius: 4,
                fontWeight: 'bold',
                marginRight: 8,
                cursor: 'pointer',
              }}
            >
              {orderEditId ? 'Update' : 'Submit'}
            </button>
            <button
              type="button"
              onClick={handleOrderCloseForm}
              style={{
                padding: '8px 16px',
                border: '1px solid #bbb',
                background: 'white',
                color: '#444',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </form>
        </div>
      )}

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {orders.length === 0 ? (
          <p>No orders found.</p>
        ) : (
          orders.map((order) => (
            <div
              key={order.order_id}
              style={{
                border: '1px solid #ddd',
                borderRadius: 8,
                padding: 16,
                width: 320,
                background: '#fff',
                boxShadow: '0 1px 2px #eee',
                position: 'relative',
              }}
            >
              <h3 style={{ margin: '8px 0' }}>
                Order #{order.order_id}
              </h3>
              <div style={{ marginBottom: 6 }}>
                <b>Customer:</b> {order.customer_name}
              </div>
              <div style={{ marginBottom: 6 }}>
                <b>Product:</b> {
                  (products.find(p => p.product_id === order.product_id)?.name) || order.product_id
                }
              </div>
              <div style={{ marginBottom: 6 }}>
                <b>Quantity:</b> {order.quantity}
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
                <button
                  style={{
                    background: '#2979ff',
                    color: 'white',
                    padding: '6px 12px',
                    border: 'none',
                    borderRadius: 4,
                    fontWeight: 'bold',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleOrderEdit(order)}
                >
                  Edit
                </button>
                <button
                  style={{
                    background: '#e53935',
                    color: 'white',
                    padding: '6px 12px',
                    border: 'none',
                    borderRadius: 4,
                    fontWeight: 'bold',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleOrderDelete(order.order_id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
