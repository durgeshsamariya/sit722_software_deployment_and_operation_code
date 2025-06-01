// frontend/product_service/src/App.jsx

import React, { useState } from 'react'; // Import useState
import ProductsPage from './pages/ProductsPage';
import OrdersPage from './pages/OrdersPage'; // Import the new OrdersPage component
import Button from './components/Button'; // Import Button for navigation

function App() {
  // State to manage which page is currently active: 'products' or 'orders'
  const [activePage, setActivePage] = useState('products'); // Default to products page

  return (
    <div className="app-container">
      {/* Global Application Header */}
      <h1 className="app-title">My E-commerce Admin Dashboard</h1>

      {/* Navigation Buttons */}
      <div className="navigation-tabs mb-lg">
        <Button
          variant={activePage === 'products' ? 'primary' : 'secondary'}
          onClick={() => setActivePage('products')}
        >
          Manage Products
        </Button>
        <Button
          variant={activePage === 'orders' ? 'primary' : 'secondary'}
          onClick={() => setActivePage('orders')}
          className="ml-sm"
        >
          Manage Orders
        </Button>
      </div>

      {/* Conditionally render the active page */}
      {activePage === 'products' ? (
        <ProductsPage />
      ) : (
        <OrdersPage />
      )}
    </div>
  );
}

export default App;