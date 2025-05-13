// src/App.jsx
import { useEffect, useState } from 'react';

function App() {
  const [products, setProducts] = useState([]);

  // Fetch products from Node.js backend
  useEffect(() => {
    fetch('http://localhost:4000/products')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch((err) => console.error('Error fetching products:', err));
  }, []);

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
    </div>
  );
}

export default App;
