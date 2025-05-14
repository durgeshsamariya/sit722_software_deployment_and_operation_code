import { useEffect, useState } from 'react'

function App() {
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])

  useEffect(() => {
    fetch('http://localhost:8000/products')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch((err) => console.error('Error fetching products:', err))
  }, [])

  useEffect(() => {
    fetch('http://localhost:8001/orders')
      .then((res) => res.json())
      .then((data) => setOrders(data))
      .catch((err) => console.error('Error fetching orders:', err))
  }, [])

  return (
    <div style={{ padding: '2rem' }}>
      <h1>Product List</h1>
      {products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        <ul>
          {products.map((product) => (
            <li key={product.id}>
              <strong>{product.name}</strong>: {product.description}
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
          {orders.map((order) => (
            <li key={order.id}>
              <strong>{order.customer_name}</strong> ordered: {order.item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default App
