import { useEffect, useState } from 'react';

// For simplicity, we'll use a hardcoded customer ID for now.
// In a real application, you'd fetch/select a customer from a Customer Service.
const DEFAULT_CUSTOMER_ID = 1;

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderErrors, setOrderErrors] = useState({});

  // State for current item being added to a new order
  const [currentItem, setCurrentItem] = useState({
    product_id: '',
    quantity: '',
  });

  // State for the list of items for the new order being created
  const [newOrderItems, setNewOrderItems] = useState([]);

  // Fetch orders and products
  const fetchOrders = () => {
    fetch('http://localhost:8001/orders/')
      .then((res) => res.json())
      .then((data) => setOrders(data))
      .catch(() => setOrders([]));
  };

  const fetchProducts = () => {
    fetch('http://localhost:8000/products/')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setProducts([]));
  };

  useEffect(() => {
    fetchOrders();
    fetchProducts();
    // Optional: Poll for order status updates more frequently for demo purposes
    // This makes the status update without manual refresh
    const interval = setInterval(fetchOrders, 5000); // Fetch every 5 seconds
    return () => clearInterval(interval); // Cleanup on unmount
  }, []);

  // Order Handlers
  const handleOrderOpenForm = () => {
    // RESET NEW ORDER FORM
    setCurrentItem({ product_id: '', quantity: '' });
    setNewOrderItems([]);
    setOrderErrors({}); // Clear previous errors
    setShowOrderForm(true);
  };

  const handleOrderCloseForm = () => {
    setShowOrderForm(false);
  };

  const handleOrderDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this order?')) return;
    try {
      const res = await fetch(`http://localhost:8001/orders/${id}`, { method: 'DELETE' });
      if (res.status === 204) {
        alert('Order deleted successfully. Note: Stock re-adjustment on deletion is an advanced feature not covered here.');
        fetchOrders();
      } else {
        const errorData = await res.json();
        alert(`Failed to delete order: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error deleting order:', error);
      alert('An error occurred while deleting the order.');
    }
  };

  // Handle changes for adding a single item to the current order
  const handleCurrentItemChange = (e) => {
    setCurrentItem({ ...currentItem, [e.target.name]: e.target.value });
  };

  // Add current item to the newOrderItems list
  const handleAddItemToOrder = () => {
    const { product_id, quantity } = currentItem;
    // Clear any previous 'items' error
    setOrderErrors(prev => ({...prev, items: undefined}));

    if (!product_id || !quantity || Number(quantity) <= 0) {
      alert('Please select a product and enter a valid quantity.');
      return;
    }

    const existingItemIndex = newOrderItems.findIndex(item => item.product_id === Number(product_id));
    if (existingItemIndex > -1) {
      // If item already exists, update quantity
      const updatedItems = [...newOrderItems];
      updatedItems[existingItemIndex].quantity += Number(quantity);
      setNewOrderItems(updatedItems);
    } else {
      // Add new item
      setNewOrderItems([...newOrderItems, { product_id: Number(product_id), quantity: Number(quantity) }]);
    }

    // Reset current item form for next entry
    setCurrentItem({ product_id: '', quantity: '' });
  };


  const handleOrderSubmit = async (e) => {
    e.preventDefault();
    setOrderErrors({});

    // IMPORTANT: Frontend validation to prevent sending empty items list
    if (newOrderItems.length === 0) {
      setOrderErrors({ items: 'You must add at least one item to the order.' }); // Make this error more prominent
      return; // Stop submission
    }

    const payload = {
      customer_id: DEFAULT_CUSTOMER_ID,
      items: newOrderItems,
    };

    try {
      const res = await fetch('http://localhost:8001/orders/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.status === 202) {
        alert('Order submitted successfully. Stock confirmation is pending!');
        setShowOrderForm(false);
        fetchOrders(); // Fetch orders to show the new one with 'pending_stock_check' status
      } else if (res.status === 422) {
        const errorData = await res.json();
        const fieldErrors = {};
        if (errorData && errorData.detail) {
          for (const err of errorData.detail) {
            const loc = err.loc[err.loc.length - 1];
            fieldErrors[loc] = err.msg;
          }
        }
        setOrderErrors(fieldErrors);
      } else {
        const errorData = await res.json();
        alert(`Failed to create order: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error submitting order:', error);
      alert('An error occurred while submitting the order.');
    }
  };

  // Helper to get product name by ID
  const getProductName = (productId) => {
    return products.find(p => p.product_id === productId)?.name || `Product ID: ${productId}`;
  };

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
          <h2 style={{ color: 'black' }}>Add New Order</h2>
          <form onSubmit={handleOrderSubmit} autoComplete="off" style={{ color: 'black', padding: 10 }}>
            {/* Customer ID (hardcoded for simplicity) */}
            <div style={{ marginBottom: 16, color: 'black' }}>
              <label>
                Customer ID:
                <input
                  type="number"
                  value={DEFAULT_CUSTOMER_ID}
                  readOnly
                  style={{ width: '100%', padding: 8, marginTop: 4, background: '#e0e0e0', cursor: 'not-allowed' }}
                />
              </label>
              {orderErrors.customer_id && (
                <div style={{ color: 'red', fontSize: 12 }}>{orderErrors.customer_id}</div>
              )}
            </div>

            {/* Section for adding items to the current order */}
            <h3 style={{ borderBottom: '1px solid #eee', paddingBottom: 8, marginBottom: 16 }}>Add Items</h3>
            <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'flex-end' }}>
              <div style={{ flex: 2 }}>
                <label>
                  Product:
                  <select
                    name="product_id"
                    value={currentItem.product_id}
                    onChange={handleCurrentItemChange}
                    style={{ width: '100%', padding: 8, marginTop: 4 }}
                  >
                    <option value="">Select product...</option>
                    {products.map((prod) => (
                      <option key={prod.product_id} value={prod.product_id}>
                        {prod.name} (Stock: {prod.stock_quantity})
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div style={{ flex: 1 }}>
                <label>
                  Quantity:
                  <input
                    type="number"
                    name="quantity"
                    value={currentItem.quantity}
                    onChange={handleCurrentItemChange}
                    style={{ width: '100%', padding: 8, marginTop: 4 }}
                    min="1"
                  />
                </label>
              </div>
              <button
                type="button"
                onClick={handleAddItemToOrder}
                style={{
                  background: '#66bb6a',
                  color: 'white',
                  padding: '8px 12px',
                  border: 'none',
                  borderRadius: 4,
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                Add Item
              </button>
            </div>

            {/* Display items currently in the new order - IMPROVED STYLING */}
            {newOrderItems.length > 0 && (
              <div style={{ marginBottom: 16, border: '1px solid #ddd', padding: 10, borderRadius: 4, background: '#f0f8ff' }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#333' }}>Items in Order:</h4>
                <ul style={{ margin: '0', padding: '0 0 0 20px', listStyleType: 'disc', color: '#555' }}>
                  {newOrderItems.map((item, index) => (
                    <li key={index} style={{ marginBottom: 5 }}>
                      {getProductName(item.product_id)} - Quantity: {item.quantity}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {orderErrors.items && (
              // IMPROVED ERROR VISIBILITY
              <div style={{ color: 'red', fontSize: 14, marginBottom: 16, fontWeight: 'bold', border: '1px solid red', padding: '8px', borderRadius: '4px', background: '#ffebee' }}>
                {orderErrors.items}
              </div>
            )}

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
              Submit Order
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

      {/* Display Existing Orders */}
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
              {/* Display status with consistent styling */}
              <div style={{ marginBottom: 6, fontWeight: 'bold', color:
                order.status === 'confirmed' ? '#4CAF50' : // Green for confirmed
                order.status === 'pending_stock_check' ? '#FFC107' : // Orange for pending
                '#F44336' // Red for failed/cancelled
              }}>
                Status: {order.status ? order.status.replace(/_/g, ' ').toUpperCase() : 'UNKNOWN'}
              </div>
              <div style={{ marginBottom: 6, color: '#333' }}>
                <b>Customer ID:</b> {order.customer_id}
              </div>
              
              {/* Iterate and display multiple items - IMPROVED STYLING */}
              <div style={{ marginBottom: 6, color: '#333' }}>
                <b>Items:</b>
                <ul style={{ margin: '5px 0 0 20px', padding: 0, listStyleType: 'disc', color: '#555' }}>
                  {order.items && order.items.length > 0 ? (
                    order.items.map((item, index) => (
                      <li key={index} style={{ marginBottom: 5 }}>
                        {getProductName(item.product_id)} (Qty: {item.quantity})
                      </li>
                    ))
                  ) : (
                    <li style={{ color: '#aaa' }}>No items found</li>
                  )}
                </ul>
              </div>

              {/* Removed Edit button for simplicity in Week 4 */}
              <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
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
  );
}