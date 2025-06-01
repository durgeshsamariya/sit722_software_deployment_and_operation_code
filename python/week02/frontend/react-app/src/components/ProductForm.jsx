// /components/ProductForm.jsx

import React from 'react';
import InputField from './InputField'; // Import the reusable InputField component
import Button from './Button';         // Import the reusable Button component

function ProductForm({
  form,
  fieldErrors,
  isSubmitting,
  editId,
  handleChange,
  handleSubmit,
  onCloseForm,
  globalError // Prop for displaying general form errors if any
}) {
  return (
    <div className="form-container">
      <h2>{editId ? 'Edit Product' : 'Add New Product'}</h2>
      {globalError && (
        <div className="status-message error mb-md">
          {globalError}
        </div>
      )}
      <form onSubmit={handleSubmit} autoComplete="off">
        <InputField
          label="Name"
          id="name"
          name="name"
          value={form.name}
          onChange={handleChange}
          error={fieldErrors.name}
          required
          placeholder="Enter product name"
        />
        <InputField
          label="Description"
          id="description"
          name="description"
          type="textarea"
          value={form.description}
          onChange={handleChange}
          error={fieldErrors.description}
          rows={3}
          required
          placeholder="Enter product description"
        />
        <InputField
          label="Price"
          id="price"
          name="price"
          type="number"
          value={form.price}
          onChange={handleChange}
          error={fieldErrors.price}
          step="0.01"
          required
          placeholder="e.g., 9.99"
        />
        <InputField
          label="Stock Quantity"
          id="stock_quantity"
          name="stock_quantity"
          type="number"
          value={form.stock_quantity}
          onChange={handleChange}
          error={fieldErrors.stock_quantity}
          required
          placeholder="e.g., 100"
        />
        <div className="form-actions">
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? (editId ? 'Updating...' : 'Adding...') : (editId ? 'Update Product' : 'Add Product')}
          </Button>
          <Button type="button" variant="secondary" onClick={onCloseForm} disabled={isSubmitting}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

export default ProductForm;