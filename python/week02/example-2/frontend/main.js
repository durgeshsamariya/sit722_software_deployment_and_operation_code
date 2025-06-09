document.addEventListener('DOMContentLoaded', () => {
    // API endpoint for the product service.
    // When running Docker Compose, the browser on your host machine will access
    // the product service via localhost:8000 because of port mapping.
    // If frontend and backend were in the same Docker network AND frontend made
    // server-side requests, it would use 'http://product_service:8000'.
    const API_BASE_URL = 'http://localhost:8000';

    const productListDiv = document.getElementById('product-list');
    const productForm = document.getElementById('product-form');
    const messageBox = document.getElementById('message-box');

    // Function to display messages to the user
    function showMessage(message, type = 'success') {
        messageBox.textContent = message;
        messageBox.className = `message-box ${type}`; // Add type for styling (e.g., 'success', 'error')
        messageBox.style.display = 'block';
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 5000); // Hide after 5 seconds
    }

    // Function to fetch and display products
    async function fetchProducts() {
        productListDiv.innerHTML = '<p>Loading products...</p>';
        try {
            const response = await fetch(`${API_BASE_URL}/products/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const products = await response.json();
            
            productListDiv.innerHTML = ''; // Clear previous content
            if (products.length === 0) {
                productListDiv.innerHTML = '<p>No products available yet. Add some above!</p>';
                return;
            }

            products.forEach(product => {
                const productCard = document.createElement('div');
                productCard.className = 'product-card';
                productCard.innerHTML = `
                    <h3>${product.name} (ID: ${product.product_id})</h3>
                    <p>${product.description || 'No description available.'}</p>
                    <p class="price">$${product.price.toFixed(2)}</p>
                    <p class="stock">Stock: ${product.stock_quantity}</p>
                    <p><small>Created: ${new Date(product.created_at).toLocaleString()}</small></p>
                    <p><small>Last Updated: ${new Date(product.updated_at).toLocaleString()}</small></p>
                    <button class="delete-btn" data-id="${product.product_id}">Delete</button>
                `;
                productListDiv.appendChild(productCard);
            });
        } catch (error) {
            console.error('Error fetching products:', error);
            showMessage(`Failed to load products: ${error.message}`, 'error');
            productListDiv.innerHTML = '<p>Could not load products. Please check the backend service.</p>';
        }
    }

    // Handle form submission for adding a new product
    productForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const name = document.getElementById('product-name').value;
        const price = parseFloat(document.getElementById('product-price').value);
        const stock_quantity = parseInt(document.getElementById('product-stock').value, 10);
        const description = document.getElementById('product-description').value;

        const newProduct = { name, price, stock_quantity, description };

        try {
            const response = await fetch(`${API_BASE_URL}/products/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newProduct),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
            }

            const addedProduct = await response.json();
            showMessage(`Product "${addedProduct.name}" added successfully!`);
            productForm.reset(); // Clear the form
            fetchProducts(); // Refresh the list of products
        } catch (error) {
            console.error('Error adding product:', error);
            showMessage(`Error adding product: ${error.message}`, 'error');
        }
    });

    // Handle delete button clicks using event delegation
    productListDiv.addEventListener('click', async (event) => {
        if (event.target.classList.contains('delete-btn')) {
            const productId = event.target.dataset.id;
            if (!confirm(`Are you sure you want to delete product ID: ${productId}?`)) {
                return; // User cancelled
            }
            try {
                const response = await fetch(`${API_BASE_URL}/products/${productId}`, {
                    method: 'DELETE',
                });

                if (response.status === 204) { // 204 No Content is expected for successful DELETE
                    showMessage(`Product ID: ${productId} deleted successfully.`);
                    fetchProducts(); // Refresh the list
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
                }
            } catch (error) {
                console.error('Error deleting product:', error);
                showMessage(`Error deleting product: ${error.message}`, 'error');
            }
        }
    });

    // Initial fetch of products when the page loads
    fetchProducts();
});
