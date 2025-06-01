// /src/pages/ProductsPage.jsx

import React, { useEffect, useState } from 'react';
import ProductCard from '../components/ProductCard'; // Import ProductCard
import ProductForm from '../components/ProductForm'; // Import ProductForm
import Button from '../components/Button';           // Import Button (for Add Product button)

function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    stock_quantity: '',
  });
  const [fieldErrors, setFieldErrors] = useState({}); // For validation errors from API or client
  const [globalError, setGlobalError] = useState(null); // For general API/network errors
  const [editId, setEditId] = useState(null); // Track if editing
  const [isLoading, setIsLoading] = useState(true); // For initial product fetch
  const [isSubmitting, setIsSubmitting] = useState(false); // For form submission

  const API_BASE_URL = 'http://localhost:8000'; // Define API base URL here

  // --- Fetch Products ---
  const fetchProducts = async () => {
    setIsLoading(true);
    setGlobalError(null); // Clear previous global errors
    try {
      const response = await fetch(`${API_BASE_URL}/products/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      console.error("Failed to fetch products:", error);
      setGlobalError("Failed to load products. Please check server connection.");
      setProducts([]); // Ensure products array is empty on error
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch products on component mount
  useEffect(() => {
    fetchProducts();
  }, []);

  // --- Form Handling ---

  const handleOpenForm = () => {
    setForm({ name: '', description: '', price: '', stock_quantity: '' });
    setFieldErrors({}); // Clear field-specific errors
    setGlobalError(null); // Clear global errors
    setEditId(null);
    setShowForm(true);
  };

  const handleEdit = (product) => {
    setForm({
      name: product.name || '',
      description: product.description || '',
      price: product.price !== undefined ? product.price : '',
      stock_quantity: product.stock_quantity !== undefined ? product.stock_quantity : '',
    });
    setFieldErrors({});
    setGlobalError(null);
    setEditId(product.product_id);
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
    // Clear error for the field as user types
    if (fieldErrors[name]) {
      setFieldErrors((prevErrors) => ({ ...prevErrors, [name]: undefined }));
    }
  };

  // Client-side validation
  const validateForm = () => {
    const newErrors = {};
    if (!form.name.trim()) newErrors.name = 'Product name is required.';
    if (!form.description.trim()) newErrors.description = 'Description is required.';
    if (form.price === '' || isNaN(Number(form.price)) || Number(form.price) <= 0) {
      newErrors.price = 'Price must be a positive number.';
    }
    if (form.stock_quantity === '' || isNaN(Number(form.stock_quantity)) || Number(form.stock_quantity) < 0) {
      newErrors.stock_quantity = 'Stock quantity must be a non-negative number.';
    }
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const clientErrors = validateForm();
    if (Object.keys(clientErrors).length > 0) {
      setFieldErrors(clientErrors);
      setGlobalError(null); // Clear global error if client errors exist
      return;
    }

    setIsSubmitting(true);
    setFieldErrors({}); // Clear previous field errors
    setGlobalError(null); // Clear previous global errors

    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      stock_quantity: Number(form.stock_quantity),
    };

    try {
      let response;
      if (editId) {
        response = await fetch(`${API_BASE_URL}/products/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        response = await fetch(`${API_BASE_URL}/products/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (response.ok) { // Status 200-299
        handleCloseForm(); // Close form and reset state
        fetchProducts(); // Refresh product list
      } else if (response.status === 422) {
        // FastAPI validation errors
        const errorData = await response.json();
        const apiFieldErrors = {};
        if (errorData && errorData.detail) {
          for (const err of errorData.detail) {
            const loc = err.loc[err.loc.length - 1]; // Get the field name
            apiFieldErrors[loc] = err.msg;
          }
        }
        setFieldErrors(apiFieldErrors);
        setGlobalError("Please correct the form errors.");
      } else {
        // Other API errors (400, 500, etc.)
        const errorText = await response.text(); // Get raw text if JSON parsing fails
        console.error("API Error:", response.status, errorText);
        setGlobalError(`Server error: ${response.status}. Please try again.`);
      }
    } catch (networkError) {
      // Network errors (e.g., server unreachable)
      console.error("Network error during submission:", networkError);
      setGlobalError("A network error occurred. Please check your connection.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Delete Handling ---
  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this product? This action cannot be undone.')) {
      return;
    }
    setGlobalError(null); // Clear previous global errors
    setIsLoading(true); // Show loading while deleting
    try {
      const response = await fetch(`${API_BASE_URL}/products/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`Failed to delete product. Status: ${response.status}`);
      }
      fetchProducts(); // Refresh product list after deletion
    } catch (error) {
      console.error("Error deleting product:", error);
      setGlobalError("Failed to delete product. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // --- Render ---
  return (
    <> {/* Using a React Fragment as this is a section within App.jsx */}
      {globalError && (
        <div className="status-message error">
          {globalError}
        </div>
      )}

      {/* Button to open the form */}
      <Button variant="primary" onClick={handleOpenForm} className="mb-lg">
        Add New Product
      </Button>

      {/* Product Form (conditionally rendered) */}
      {showForm && (
        <ProductForm
          form={form}
          fieldErrors={fieldErrors}
          isSubmitting={isSubmitting}
          editId={editId}
          handleChange={handleChange}
          handleSubmit={handleSubmit}
          onCloseForm={handleCloseForm}
          globalError={globalError} // Pass globalError down to form for display
        />
      )}

      {/* Product List */}
      {isLoading && products.length === 0 && !globalError ? (
        <p className="status-message loading">Loading products...</p>
      ) : products.length === 0 && !globalError ? (
        <p className="status-message">No products found. Add one to get started!</p>
      ) : (
        <div className="product-list-grid">
          {products.map((product) => (
            <ProductCard
              key={product.product_id}
              product={product}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </>
  );
}

export default ProductsPage;