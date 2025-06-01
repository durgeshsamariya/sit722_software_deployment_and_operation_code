// frontend/product_service/src/App.jsx

import React from 'react';
import ProductsPage from './pages/ProductsPage'; // Import the new ProductsPage component

function App() {
  return (
    <div className="app-container">
      <h1>Product Catalog</h1>
      <ProductsPage /> {/* Render the main products page */}
    </div>
  );
}

export default App;