// src/App.jsx
import { useEffect, useState } from 'react'

function App() {
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])

  // Fetch products from Node.js backend on port 4000
  useEffect(() => {
    fetch('http://localhost:8000/products')
      .then(res => res.json())
      .then(data => setProducts(data))
      .catch(err => console.error('Error fetching products:', err))
  }, [])

  // Fetch orders from Node.js backend on port 4001
  useEffect(() => {
    fetch('http://localhost:8001/orders')
      .then(res => res.json())
      .then(data => setOrders(data))
      .catch(err => console.error('Error fetching orders:', err))
  }, [])

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Product List</h1>
      {products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        <ul>
          {products.map(p => (
            <li key={p.id}>
              <strong>{p.name}</strong>: {p.description}
            </li>
          ))}
        </ul>
      )}

      <hr style={{ margin: '2rem 0' }} />

      <h1>Order List</h1>
      {orders.length === 0 ? (
        <p>No orders found.</p>
      ) : (
        <ul>
          {orders.map(o => (
            <li key={o.id}>
              <strong>{o.customer_name}</strong> ordered: {o.item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default App
