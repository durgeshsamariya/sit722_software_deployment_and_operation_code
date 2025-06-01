// /src/components/OrderForm.jsx

import React from 'react';
import InputField from './InputField'; // Reusing your InputField component
import Button from './Button';         // Reusing your Button component

function OrderForm({
  form,
  fieldErrors,
  isSubmitting,
  editId, // This will be order_id for editing
  handleChange,
  handleSubmit,
  onCloseForm,
  globalError
}) {
  return (
    <div className="form-container">
      <h2>{editId ? 'Edit Order' : 'Create New Order'}</h2>
      {globalError && (
        <div className="status-message error mb-md">
          {globalError}
        </div>
      )}
      <form onSubmit={handleSubmit} autoComplete="off">
        <InputField
          label="Product ID"
          id="product_id"
          name="product_id"
          type="number"
          value={form.product_id}
          onChange={handleChange}
          error={fieldErrors.product_id}
          required
          placeholder="Enter product ID"
        />
        <InputField
          label="Quantity"
          id="quantity"
          name="quantity"
          type="number"
          value={form.quantity}
          onChange={handleChange}
          error={fieldErrors.quantity}
          required
          placeholder="e.g., 5"
        />
        <InputField
          label="Customer Name"
          id="customer_name"
          name="customer_name"
          type="text"
          value={form.customer_name}
          onChange={handleChange}
          error={fieldErrors.customer_name}
          required
          placeholder="Enter customer name"
        />

        <div className="form-actions">
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? (editId ? 'Updating...' : 'Creating...') : (editId ? 'Update Order' : 'Create Order')}
          </Button>
          <Button type="button" variant="secondary" onClick={onCloseForm} disabled={isSubmitting}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

export default OrderForm;