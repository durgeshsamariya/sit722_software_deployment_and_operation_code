// week03/example-3/frontend/main.js

document.addEventListener('DOMContentLoaded', () => {
    // API endpoints for the Product, Order, and Customer services.
    // These ports are mapped from the Docker containers to the host machine in docker-compose.yml.
    const PRODUCT_API_BASE_URL = 'http://localhost:8000';
    const ORDER_API_BASE_URL = 'http://localhost:8001';
    const CUSTOMER_API_BASE_URL = 'http://localhost:8002'; // NEW: Customer Service

    // DOM Elements
    const messageBox = document.getElementById('message-box');
    const productForm = document.getElementById('product-form');
    const productListDiv = document.getElementById('product-list');
    const customerForm = document.getElementById('customer-form'); // NEW: Customer Form
    const customerListDiv = document.getElementById('customer-list'); // NEW: Customer List
    const cartItemsList = document.getElementById('cart-items');
    const cartTotalSpan = document.getElementById('cart-total');
    const placeOrderForm = document.getElementById('place-order-form');
    const orderListDiv = document.getElementById('order-list');

    // Shopping Cart State
    let cart = [];
    let productsCache = {}; // Cache products fetched to easily get details for cart items

    // --- Utility Functions ---

    // Function to display messages to the user (success, error, info)
    function showMessage(message, type = 'info') {
        messageBox.textContent = message;
        messageBox.className = `message-box ${type}`;
        messageBox.style.display = 'block';
        // Hide after 5 seconds
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 5000);
    }

    // Function to format currency
    function formatCurrency(amount) {
        return `$${parseFloat(amount).toFixed(2)}`;
    }

    // --- Product Service Interactions ---

    // Fetch and display products
    async function fetchProducts() {
        productListDiv.innerHTML = '<p>Loading products...</p>';
        try {
            const response = await fetch(`${PRODUCT_API_BASE_URL}/products/`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const products = await response.json();
            
            productListDiv.innerHTML = ''; // Clear previous content
            productsCache = {}; // Clear existing cache

            if (products.length === 0) {
                productListDiv.innerHTML = '<p>No products available yet. Add some above!</p>';
                return;
            }

            products.forEach(product => {
                productsCache[product.product_id] = product; // Cache product details
                const productCard = document.createElement('div');
                productCard.className = 'product-card';
                
                productCard.innerHTML = `
                    <img src="${product.image_url || 'https://placehold.co/300x200/cccccc/333333?text=No+Image'}" alt="${product.name}" onerror="this.onerror=null;this.src='https://placehold.co/300x200/cccccc/333333?text=Image+Error';" />
                    <h3>${product.name} (ID: ${product.product_id})</h3>
                    <p>${product.description || 'No description available.'}</p>
                    <p class="price">${formatCurrency(product.price)}</p>
                    <p class="stock">Stock: ${product.stock_quantity}</p>
                    <p><small>Created: ${new Date(product.created_at).toLocaleString()}</small></p>
                    <p><small>Last Updated: ${new Date(product.updated_at).toLocaleString()}</small></p>
                    <div class="upload-image-group">
                        <label for="image-upload-${product.product_id}">Upload Image:</label>
                        <input type="file" id="image-upload-${product.product_id}" accept="image/*" data-product-id="${product.product_id}">
                        <button class="upload-btn" data-id="${product.product_id}">Upload Photo</button>
                    </div>
                    <div class="card-actions">
                        <button class="add-to-cart-btn" data-id="${product.product_id}" data-name="${product.name}" data-price="${product.price}">Add to Cart</button>
                        <button class="delete-btn" data-id="${product.product_id}">Delete</button>
                    </div>
                `;
                productListDiv.appendChild(productCard);
            });
        } catch (error) {
            console.error('Error fetching products:', error);
            showMessage(`Failed to load products: ${error.message}`, 'error');
            productListDiv.innerHTML = '<p>Could not load products. Please check the Product Service.</p>';
        }
    }

    // Handle form submission for adding a new product
    productForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const name = document.getElementById('product-name').value;
        const price = parseFloat(document.getElementById('product-price').value);
        const stock_quantity = parseInt(document.getElementById('product-stock').value, 10);
        const description = document.getElementById('product-description').value;

        const newProduct = { name, price, stock_quantity, description };

        try {
            const response = await fetch(`${PRODUCT_API_BASE_URL}/products/`, {
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
            showMessage(`Product "${addedProduct.name}" added successfully! ID: ${addedProduct.product_id}`, 'success');
            productForm.reset(); // Clear the form
            fetchProducts(); // Refresh the list of products
        } catch (error) {
            console.error('Error adding product:', error);
            showMessage(`Error adding product: ${error.message}`, 'error');
        }
    });

    // Handle product card actions (delete, add to cart, upload image)
    productListDiv.addEventListener('click', async (event) => {
        // Delete Product
        if (event.target.classList.contains('delete-btn')) {
            const productId = event.target.dataset.id;
            if (!confirm(`Are you sure you want to delete product ID: ${productId}?`)) {
                return;
            }
            try {
                const response = await fetch(`${PRODUCT_API_BASE_URL}/products/${productId}`, {
                    method: 'DELETE',
                });

                if (response.status === 204) {
                    showMessage(`Product ID: ${productId} deleted successfully.`, 'success');
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

        // Add to Cart
        if (event.target.classList.contains('add-to-cart-btn')) {
            const productId = event.target.dataset.id;
            const productName = event.target.dataset.name;
            const productPrice = parseFloat(event.target.dataset.price);
            
            addToCart(productId, productName, productPrice);
        }

        // Upload Product Image
        if (event.target.classList.contains('upload-btn')) {
            const productId = event.target.dataset.id;
            const fileInput = document.getElementById(`image-upload-${productId}`);
            const file = fileInput.files[0];

            if (!file) {
                showMessage("Please select an image file to upload.", 'info');
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            try {
                showMessage(`Uploading image for product ${productId}...`, 'info');
                const response = await fetch(`${PRODUCT_API_BASE_URL}/products/${productId}/upload-image`, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
                }

                const updatedProduct = await response.json();
                showMessage(`Image uploaded successfully for product ${updatedProduct.name}!`, 'success');
                fileInput.value = ''; // Clear file input
                fetchProducts(); // Refresh products to show new image URL
            } catch (error) {
                console.error('Error uploading image:', error);
                showMessage(`Error uploading image: ${error.message}`, 'error');
            }
        }
    });


    // --- Shopping Cart Functions ---

    function addToCart(productId, productName, productPrice) {
        const existingItemIndex = cart.findIndex(item => item.product_id === productId);

        if (existingItemIndex !== -1) {
            cart[existingItemIndex].quantity += 1;
        } else {
            cart.push({
                product_id: productId,
                name: productName,
                price: productPrice,
                quantity: 1
            });
        }
        updateCartDisplay();
        showMessage(`Added "${productName}" to cart!`, 'info');
    }

    function updateCartDisplay() {
        cartItemsList.innerHTML = '';
        let totalCartAmount = 0;

        if (cart.length === 0) {
            cartItemsList.innerHTML = '<li>Your cart is empty.</li>';
        } else {
            cart.forEach(item => {
                const li = document.createElement('li');
                const itemTotal = item.quantity * item.price;
                totalCartAmount += itemTotal;
                li.innerHTML = `
                    <span>${item.name} (x${item.quantity})</span>
                    <span>${formatCurrency(item.price)} each - ${formatCurrency(itemTotal)}</span>
                `;
                cartItemsList.appendChild(li);
            });
        }
        cartTotalSpan.textContent = `Total: ${formatCurrency(totalCartAmount)}`;
    }


    // --- Customer Service Interactions ---

    // Fetch and display customers
    async function fetchCustomers() {
        customerListDiv.innerHTML = '<p>Loading customers...</p>';
        try {
            const response = await fetch(`${CUSTOMER_API_BASE_URL}/customers/`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const customers = await response.json();
            
            customerListDiv.innerHTML = ''; // Clear previous content

            if (customers.length === 0) {
                customerListDiv.innerHTML = '<p>No customers available yet. Add some above!</p>';
                return;
            }

            customers.forEach(customer => {
                const customerCard = document.createElement('div');
                customerCard.className = 'customer-card';
                customerCard.innerHTML = `
                    <h3>${customer.first_name} ${customer.last_name} (ID: ${customer.customer_id})</h3>
                    <p>Email: ${customer.email}</p>
                    <p>Phone: ${customer.phone_number || 'N/A'}</p>
                    <p>Shipping Address: ${customer.shipping_address || 'N/A'}</p>
                    <p><small>Created: ${new Date(customer.created_at).toLocaleString()}</small></p>
                    <div class="card-actions">
                        <button class="delete-customer-btn" data-id="${customer.customer_id}">Delete</button>
                    </div>
                `;
                customerListDiv.appendChild(customerCard);
            });
        } catch (error) {
            console.error('Error fetching customers:', error);
            showMessage(`Failed to load customers: ${error.message}`, 'error');
            customerListDiv.innerHTML = '<p>Could not load customers. Please check the Customer Service.</p>';
        }
    }

    // Handle form submission for adding a new customer
    customerForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const email = document.getElementById('customer-email').value;
        const password = document.getElementById('customer-password').value;
        const first_name = document.getElementById('customer-first-name').value;
        const last_name = document.getElementById('customer-last-name').value;
        const phone_number = document.getElementById('customer-phone').value;
        const shipping_address = document.getElementById('customer-shipping-address').value;

        const newCustomer = { email, password, first_name, last_name, phone_number, shipping_address };

        try {
            const response = await fetch(`${CUSTOMER_API_BASE_URL}/customers/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newCustomer),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
            }

            const addedCustomer = await response.json();
            showMessage(`Customer "${addedCustomer.email}" added successfully! ID: ${addedCustomer.customer_id}`, 'success');
            customerForm.reset(); // Clear the form
            fetchCustomers(); // Refresh the list of customers
        } catch (error) {
            console.error('Error adding customer:', error);
            showMessage(`Error adding customer: ${error.message}`, 'error');
        }
    });

    // Handle customer delete buttons (using event delegation)
    customerListDiv.addEventListener('click', async (event) => {
        if (event.target.classList.contains('delete-customer-btn')) {
            const customerId = event.target.dataset.id;
            if (!confirm(`Are you sure you want to delete customer ID: ${customerId}?`)) {
                return;
            }
            try {
                const response = await fetch(`${CUSTOMER_API_BASE_URL}/customers/${customerId}`, {
                    method: 'DELETE',
                });

                if (response.status === 204) {
                    showMessage(`Customer ID: ${customerId} deleted successfully.`, 'success');
                    fetchCustomers(); // Refresh the list
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
                }
            } catch (error) {
                console.error('Error deleting customer:', error);
                showMessage(`Error deleting customer: ${error.message}`, 'error');
            }
        }
    });


    // --- Order Service Interactions ---

    // Handle form submission for placing a new order
    placeOrderForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (cart.length === 0) {
            showMessage("Your cart is empty. Add products before placing an order.", 'info');
            return;
        }

        const userId = parseInt(document.getElementById('order-user-id').value, 10);
        const shippingAddress = document.getElementById('shipping-address').value;

        // Map cart items to OrderItemCreate schema
        const orderItems = cart.map(item => ({
            product_id: parseInt(item.product_id, 10),
            quantity: item.quantity,
            price_at_purchase: item.price
        }));

        const newOrder = {
            user_id: userId,
            shipping_address: shippingAddress,
            items: orderItems
        };

        try {
            // Order service will now create order with 'pending' status
            // and publish an event for stock deduction.
            showMessage("Placing order... (status will update asynchronously)", 'info');
            const response = await fetch(`${ORDER_API_BASE_URL}/orders/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newOrder),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
            }

            const placedOrder = await response.json();
            showMessage(`Order ${placedOrder.order_id} created with initial status: ${placedOrder.status}. Stock deduction pending.`, 'success');
            
            cart = []; // Clear cart after successful order placement
            updateCartDisplay();
            placeOrderForm.reset(); // Clear form
            fetchOrders(); // Refresh order list to show the new 'pending' order
            // No longer fetching products here directly, as stock update is asynchronous
        } catch (error) {
            console.error('Error placing order:', error);
            showMessage(`Error placing order: ${error.message}`, 'error');
        }
    });

    // Fetch and display orders
    async function fetchOrders() {
        orderListDiv.innerHTML = '<p>Loading orders...</p>';
        try {
            const response = await fetch(`${ORDER_API_BASE_URL}/orders/`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const orders = await response.json();
            
            orderListDiv.innerHTML = ''; // Clear previous content

            if (orders.length === 0) {
                orderListDiv.innerHTML = '<p>No orders available yet.</p>';
                return;
            }

            orders.forEach(order => {
                const orderCard = document.createElement('div');
                orderCard.className = 'order-card';
                orderCard.innerHTML = `
                    <h3>Order ID: ${order.order_id}</h3>
                    <p>User ID: ${order.user_id}</p>
                    <p>Order Date: ${new Date(order.order_date).toLocaleString()}</p>
                    <p>Status: <span id="order-status-${order.order_id}">${order.status}</span></p>
                    <p>Total Amount: ${formatCurrency(order.total_amount)}</p>
                    <p>Shipping Address: ${order.shipping_address || 'N/A'}</p>
                    <p><small>Created: ${new Date(order.created_at).toLocaleString()}</small></p>
                    <p><small>Last Updated: ${new Date(order.updated_at).toLocaleString()}</small></p>
                    
                    <h4>Items:</h4>
                    <ul class="order-items">
                        ${order.items.map(item => `
                            <li>
                                <span>Product ID: ${item.product_id}</span> - Qty: ${item.quantity} @ ${formatCurrency(item.price_at_purchase)} (Total: ${formatCurrency(item.item_total)})
                            </li>
                        `).join('')}
                    </ul>

                    <div class="status-selector">
                        <select id="status-select-${order.order_id}" data-order-id="${order.order_id}">
                            <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="processing" ${order.status === 'processing' ? 'selected' : ''}>Processing</option>
                            <option value="shipped" ${order.status === 'shipped' ? 'selected' : ''}>Shipped</option>
                            <option value="confirmed" ${order.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                            <option value="failed" ${order.status === 'failed' ? 'selected' : ''}>Failed</option> <!-- NEW: Failed Status -->
                            <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                            <option value="completed" ${order.status === 'completed' ? 'selected' : ''}>Completed</option>
                        </select>
                        <button class="status-update-btn" data-id="${order.order_id}">Update Status</button>
                    </div>
                    <div class="card-actions">
                        <button class="delete-btn" data-id="${order.order_id}">Delete Order</button>
                    </div>
                `;
                orderListDiv.appendChild(orderCard);
            });
        } catch (error) {
            console.error('Error fetching orders:', error);
            showMessage(`Failed to load orders: ${error.message}`, 'error');
            orderListDiv.innerHTML = '<p>Could not load orders. Please check the Order Service.</p>';
        }
    }

    // Handle order status update and delete buttons (using event delegation)
    orderListDiv.addEventListener('click', async (event) => {
        // Update Order Status
        if (event.target.classList.contains('status-update-btn')) {
            const orderId = event.target.dataset.id;
            const statusSelect = document.getElementById(`status-select-${orderId}`);
            const newStatus = statusSelect.value;

            try {
                showMessage(`Updating status for order ${orderId} to "${newStatus}"...`, 'info');
                const response = await fetch(`${ORDER_API_BASE_URL}/orders/${orderId}/status`, { // PATCH request now uses body
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ status: newStatus }), // Send status in body
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
                }

                const updatedOrder = await response.json();
                document.getElementById(`order-status-${orderId}`).textContent = updatedOrder.status;
                showMessage(`Order ${orderId} status updated to "${updatedOrder.status}"!`, 'success');
                fetchOrders(); // Refresh the list to reflect any changes if needed
            } catch (error) {
                console.error('Error updating order status:', error);
                showMessage(`Error updating order status: ${error.message}`, 'error');
            }
        }

        // Delete Order
        if (event.target.classList.contains('delete-btn')) {
            const orderId = event.target.dataset.id;
            if (!confirm(`Are you sure you want to delete order ID: ${orderId}? This will also delete all associated items.`)) {
                return;
            }
            try {
                const response = await fetch(`${ORDER_API_BASE_URL}/orders/${orderId}`, {
                    method: 'DELETE',
                });

                if (response.status === 204) {
                    showMessage(`Order ID: ${orderId} deleted successfully.`, 'success');
                    fetchOrders(); // Refresh the list
                } else {
                    const errorData = await response.json();
                    throw new Error(errorData.detail ? JSON.stringify(errorData.detail) : `HTTP error! status: ${response.status}`);
                }
            } catch (error) {
                console.error('Error deleting order:', error);
                showMessage(`Error deleting order: ${error.message}`, 'error');
            }
        }
    });

    // Initial data fetch on page load
    fetchProducts();
    fetchCustomers(); // NEW: Fetch customers on load
    fetchOrders();

    // Set up a periodic refresh for orders (e.g., every 10 seconds)
    // This helps show asynchronous status updates from RabbitMQ in real-time
    setInterval(fetchOrders, 10000); // Refresh orders every 10 seconds
    setInterval(fetchProducts, 15000); // Refresh products every 15 seconds to see stock changes

});
