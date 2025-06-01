// /src/pages/OrdersPage.jsx

import React, { useEffect, useState } from 'react';
import OrderList from '../components/OrderList';
import OrderForm from '../components/ProductForm'; // Assuming ProductForm was a typo and you meant OrderForm, correct this if not
import Button from '../components/Button';

function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    product_id: '',
    quantity: '',
    customer_name: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [globalError, setGlobalError] = useState(null);
  const [editId, setEditId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Use environment variables for API base URLs
  const ORDER_API_BASE_URL = import.meta.env.REACT_APP_ORDER_SERVICE_URL || 'http://localhost:8001';
  const PRODUCT_API_BASE_URL = import.meta.env.REACT_APP_PRODUCT_SERVICE_URL || 'http://localhost:8000'; // Used by OrderRow

  // --- Fetch Orders ---
  const fetchOrders = async () => {
    setIsLoading(true);
    setGlobalError(null);
    try {
      const response = await fetch(`${ORDER_API_BASE_URL}/orders/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setOrders(data);
    } catch (error) {
      console.error("Failed to fetch orders:", error);
      setGlobalError("Failed to load orders. Please check Order Service connection.");
      setOrders([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  // --- Form Handling (No changes needed here) ---
  const handleOpenForm = () => {
    setForm({ product_id: '', quantity: '', customer_name: '' });
    setFieldErrors({});
    setGlobalError(null);
    setEditId(null);
    setShowForm(true);
  };

  const handleEdit = (order) => {
    setForm({
      product_id: order.product_id || '',
      quantity: order.quantity || '',
      customer_name: order.customer_name || '',
    });
    setFieldErrors({});
    setGlobalError(null);
    setEditId(order.order_id);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditId(null);
    setFieldErrors({});
    setGlobalError(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
    if (fieldErrors[name]) {
      setFieldErrors((prevErrors) => ({ ...prevErrors, [name]: undefined }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    if (form.product_id === '' || isNaN(Number(form.product_id)) || Number(form.product_id) <= 0) {
      newErrors.product_id = 'Product ID must be a positive number.';
    }
    if (form.quantity === '' || isNaN(Number(form.quantity)) || Number(form.quantity) <= 0) {
      newErrors.quantity = 'Quantity must be a positive number.';
    }
    if (!form.customer_name.trim()) {
      newErrors.customer_name = 'Customer name is required.';
    }
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clientErrors = validateForm();
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      setGlobalError(null);
      return;
    }

    setIsSubmitting(true);
    setFieldErrors({});
    setGlobalError(null);

    const payload = {
      product_id: Number(form.product_id),
      quantity: Number(form.quantity),
      customer_name: form.customer_name.trim(),
    };

    try {
      let response;
      let url = `${ORDER_API_BASE_URL}/orders/`;
      let method = 'POST';

      if (editId) {
        url = `${ORDER_API_BASE_URL}/orders/${editId}`;
        method = 'PUT';
      }

      response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        handleCloseForm();
        fetchOrders();
      } else if (response.status === 422) {
        const errorData = await response.json();
        const apiFieldErrors = {};
        if (errorData && errorData.detail) {
          for (const err of errorData.detail) {
            const loc = err.loc[err.loc.length - 1];
            apiFieldErrors[loc] = err.msg;
          }
        }
        setFieldErrors(apiFieldErrors);
        setGlobalError("Please correct the form errors provided by the server.");
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Server error: ${response.status}`;
        console.error("API Error during order submission:", response.status, errorMessage);
        setGlobalError(`Error: ${errorMessage}. Please try again.`);
      }
    } catch (networkError) {
      console.error("Network error during order submission:", networkError);
      setGlobalError("A network error occurred. Please check your connection to the Order Service.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Order Deletion Handler (No changes needed here) ---
  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this order? This action will return the product quantity to stock.')) {
      return;
    }
    setGlobalError(null);
    setIsLoading(true);
    try {
      const response = await fetch(`${ORDER_API_BASE_URL}/orders/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Failed to delete order. Status: ${response.status}`;
        throw new Error(errorMessage);
      }
      fetchOrders();
    } catch (error) {
      console.error("Error deleting order:", error);
      setGlobalError(`Failed to delete order: ${error.message}.`);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Component Rendering ---
  return (
    <>
      {globalError && (
        <div className="status-message error">
          {globalError}
        </div>
      )}

      <Button variant="primary" onClick={handleOpenForm} className="mb-lg">
        Create New Order
      </Button>

      {showForm && (
        <OrderForm
          form={form}
          fieldErrors={fieldErrors}
          isSubmitting={isSubmitting}
          editId={editId}
          handleChange={handleChange}
          handleSubmit={handleSubmit}
          onCloseForm={handleCloseForm}
          globalError={globalError}
        />
      )}

      {isLoading && orders.length === 0 && !globalError ? (
        <p className="status-message loading">Loading orders...</p>
      ) : orders.length === 0 && !globalError ? (
        <p className="status-message">No orders found. Create one to get started!</p>
      ) : (
        <OrderList
          orders={orders}
          onEdit={handleEdit}
          onDelete={handleDelete}
          PRODUCT_API_BASE_URL={PRODUCT_API_BASE_URL}
        />
      )}
    </>
  );
}

export default OrdersPage;