import { useState } from "react"
import ProductsPage from "./pages/ProductsPage"
import OrdersPage from "./pages/OrdersPage"

export default function App() {
  const [page, setPage] = useState("products")

  return (
    <div
      style={{
        minHeight: "100vh",
        minWidth: "100vw",
        background: "#f4f6fb",
        color: "#212121",
        fontFamily: "Segoe UI, sans-serif",
        margin: 10,
        padding: 20,
      }}
    >
      <h1>Mini Ecommerce</h1>
      {/* Tab Navigation */}
      <div style={{ marginBottom: 24, display: "flex", gap: 16 }}>
        <button
          onClick={() => setPage("products")}
          style={{
            background: page === "products" ? "#2979ff" : "#f2f2f2",
            color: page === "products" ? "white" : "#2979ff",
            border: "none",
            borderRadius: 4,
            fontWeight: "bold",
            padding: "8px 16px",
            cursor: "pointer",
          }}
        >
          Products
        </button>
        <button
          onClick={() => setPage("orders")}
          style={{
            background: page === "orders" ? "#2979ff" : "#f2f2f2",
            color: page === "orders" ? "white" : "#2979ff",
            border: "none",
            borderRadius: 4,
            fontWeight: "bold",
            padding: "8px 16px",
            cursor: "pointer",
          }}
        >
          Orders
        </button>
      </div>
      {/* Page Content */}
      {page === "products" ? <ProductsPage /> : <OrdersPage />}
    </div>
  )
}
