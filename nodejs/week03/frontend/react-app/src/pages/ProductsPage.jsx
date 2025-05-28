import { useEffect, useState } from 'react'

const STORAGE_ACCOUNT = import.meta.env.VITE_STORAGE_ACCOUNT || "week03"
const CONTAINER_NAME = import.meta.env.VITE_CONTAINER_NAME || "product-images"
const STORAGE_URL = `https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER_NAME}`
const SAS_TOKEN = import.meta.env.VITE_STORAGE_SAS

export default function ProductsPage() {
  const [products, setProducts] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    description: '',
    price: '',
    stock_quantity: '',
    image_file: null,
  })
  const [errors, setErrors] = useState({})
  const [editId, setEditId] = useState(null)

  // Fetch products
  const fetchProducts = () => {
    fetch('http://localhost:8000/products/')
      .then((res) => res.json())
      .then((data) => setProducts(data))
      .catch(() => setProducts([]))
  }

  useEffect(() => {
    fetchProducts()
  }, [])

  // Form Handlers
  const handleOpenForm = () => {
    setForm({ name: '', description: '', price: '', stock_quantity: '', image_file: null })
    setErrors({})
    setEditId(null)
    setShowForm(true)
  }

  const handleEdit = (product) => {
    setForm({
      name: product.name,
      description: product.description,
      price: product.price,
      stock_quantity: product.stock_quantity,
      image_file: null,
    })
    setErrors({})
    setEditId(product.product_id)
    setShowForm(true)
  }

  const handleCloseForm = () => {
    setShowForm(false)
    setEditId(null)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return
    await fetch(`http://localhost:8000/products/${id}`, { method: 'DELETE' })
    fetchProducts()
  }

  const handleChange = (e) => {
    if (e.target.name === 'image_file') {
      setForm({ ...form, image_file: e.target.files[0] })
    } else {
      setForm({ ...form, [e.target.name]: e.target.value })
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrors({})
    const formData = new FormData()
    formData.append('name', form.name)
    formData.append('description', form.description)
    formData.append('price', form.price)
    formData.append('stock_quantity', form.stock_quantity)
    if (form.image_file) {
      formData.append('image', form.image_file)
    }
    try {
      let res
      if (editId) {
        res = await fetch(`http://localhost:8000/products/${editId}`, { method: 'PUT', body: formData })
      } else {
        res = await fetch('http://localhost:8000/products/', { method: 'POST', body: formData })
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
    } catch {}
  }

  const getImageUrl = (product) => {
    if (!product.image_url) return null
    if (product.image_url.startsWith('http')) return `${product.image_url}?${SAS_TOKEN}`
    return `${STORAGE_URL}/${product.image_url}?${SAS_TOKEN}`
  }

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
          <form onSubmit={handleSubmit} autoComplete="off" style={{ color: 'black', padding: 10 }} encType="multipart/form-data">
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
            <div style={{ marginBottom: 16 }}>
              <label>
                Image:
                <input
                  type="file"
                  name="image_file"
                  accept="image/*"
                  onChange={handleChange}
                  style={{ width: '100%', padding: 8, marginTop: 4 }}
                />
              </label>
              {errors.image && (
                <div style={{ color: 'red', fontSize: 12 }}>{errors.image}</div>
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
              {getImageUrl(product) ? (
                <img
                  src={getImageUrl(product)}
                  alt={product.name}
                  style={{
                    width: '100%',
                    height: 120,
                    objectFit: 'cover',
                    borderRadius: 6,
                    marginBottom: 8,
                  }}
                  onError={e => (e.target.style.display = "none")}
                />
              ) : (
                <div
                  style={{
                    width: '100%',
                    height: 120,
                    background: '#f2f2f2',
                    borderRadius: 6,
                    marginBottom: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#aaa',
                    fontSize: 18,
                  }}
                >No Image</div>
              )}
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
