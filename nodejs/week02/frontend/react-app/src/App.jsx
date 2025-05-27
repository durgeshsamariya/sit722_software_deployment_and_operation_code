import { useEffect, useState } from 'react'

function App() {
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    stock_quantity: '',
  })
  const [errors, setErrors] = useState({})
  const [editId, setEditId] = useState(null) // Track if editing

  const fetchProducts = () => {
    fetch('http://localhost:8000/products/')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setProducts([]))
  }

  useEffect(() => {
    fetchProducts()
  }, [])

  // Open Add Product Form
  const handleOpenForm = () => {
    setForm({ name: '', description: '', price: '', stock_quantity: '' })
    setErrors({})
    setEditId(null)
    setShowForm(true)
  }

  // Open Edit Form
  const handleEdit = (product) => {
    setForm({
      name: product.name,
      description: product.description,
      price: product.price,
      stock_quantity: product.stock_quantity,
    })
    setErrors({})
    setEditId(product.product_id)
    setShowForm(true)
  }

  const handleCloseForm = () => {
    setShowForm(false)
    setEditId(null)
  }

  // Handle Delete
  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return
    await fetch(`http://localhost:8000/products/${id}`, {
      method: 'DELETE',
    })
    fetchProducts()
  }

  // On input change
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  // On form submit (Add or Edit)
  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrors({})
    const payload = {
      name: form.name,
      description: form.description,
      price: Number(form.price),
      stock_quantity: Number(form.stock_quantity),
    }
    try {
      let res
      if (editId) {
        res = await fetch(`http://localhost:8000/products/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      } else {
        res = await fetch('http://localhost:8000/products/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      }

      if (res.status === 201 || res.status === 200) {
        setShowForm(false)
        setEditId(null)
        fetchProducts()
      } else if (res.status === 422) {
        const errorData = await res.json()
        const fieldErrors = {}
        if (errorData && errorData.detail) {
          for (const err of errorData.detail) {
            const loc = err.loc[err.loc.length - 1]
            fieldErrors[loc] = err.msg
          }
        }
        setErrors(fieldErrors)
      }
    } catch {
      // No-op for now
    }
  }

  return (
    <div 
    style={{
        minHeight: '100vh',
        minWidth: '100vw',
        background: '#f4f6fb',
        color: '#212121',
        fontFamily: 'Segoe UI, sans-serif',
        margin: 10,
        padding: 20,
      }}>
      <h1>Mini Ecommerce</h1>
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
        onClick={handleOpenForm}
      >
        Add Product
      </button>

      {showForm && (
        <div
          style={{
            border: '1px solid #eee',
            borderRadius: 8,
            padding: 25,
            marginBottom: 32,
            maxWidth: '100vw',
            width: 800,
            background: '#f9f9f9',
          }}
        >
          <h2 style={{ color: 'black' }}>{editId ? 'Edit Product' : 'Add New Product'}</h2>
          <form onSubmit={handleSubmit} autoComplete="off" style={{ color: 'black', padding: 10 }}>
            <div style={{ marginBottom: 16, color: 'black' }}>
              <label>
                Name:
                <input
                  type="text"
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  required
                />
              </label>
              {errors.name && (
                <div style={{ color: 'red', fontSize: 12 }}>{errors.name}</div>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>
                Description:
                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  rows={2}
                  required
                />
              </label>
              {errors.description && (
                <div style={{ color: 'red', fontSize: 12 }}>
                  {errors.description}
                </div>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>
                Price:
                <input
                  type="number"
                  step="0.01"
                  name="price"
                  value={form.price}
                  onChange={handleChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  required
                />
              </label>
              {errors.price && (
                <div style={{ color: 'red', fontSize: 12 }}>{errors.price}</div>
              )}
            </div>
            <div style={{ marginBottom: 16 }}>
              <label>
                Stock Quantity:
                <input
                  type="number"
                  name="stock_quantity"
                  value={form.stock_quantity}
                  onChange={handleChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                  required
                />
              </label>
              {errors.stock_quantity && (
                <div style={{ color: 'red', fontSize: 12 }}>
                  {errors.stock_quantity}
                </div>
              )}
            </div>
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
              {editId ? 'Update' : 'Submit'}
            </button>
            <button
              type="button"
              onClick={handleCloseForm}
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

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {products.length === 0 ? (
          <p>No products found.</p>
        ) : (
          products.map((product) => (
            <div
              key={product.product_id}
              style={{
                border: '1px solid #ddd',
                borderRadius: 8,
                padding: 16,
                width: 250,
                background: '#fff',
                boxShadow: '0 1px 2px #eee',
                position: 'relative',
              }}
            >
              <h3 style={{ margin: '8px 0' }}>{product.name}</h3>
              <p style={{ color: '#666', minHeight: 40 }}>
                {product.description}
              </p>
              <div style={{ fontWeight: 'bold', color: '#1976d2' }}>
                ${product.price}
              </div>
              <div style={{ color: '#444', marginTop: 4 }}>
                Stock: {product.stock_quantity}
              </div>
              {/* Edit and Delete Buttons */}
              <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
                <button
                  style={{
                    background: '#2979ff',
                    color: 'white',
                    padding: '6px 12px',
                    border: 'none',
                    borderRadius: 4,
                    fontWeight: 'bold',
                    cursor: 'pointer',
                  }}
                  onClick={() => handleEdit(product)}
                >
                  Edit
                </button>
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
                  onClick={() => handleDelete(product.product_id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default App
