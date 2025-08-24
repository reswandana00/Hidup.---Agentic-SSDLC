from flask import Flask, request, jsonify, session
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Used for session management

# --- Mock Database ---
# In a real application, this would interact with a MySQL database.
# For demonstration, we use in-memory dictionaries.

users = {
    "cashier1": {"password": "password123", "role": "cashier"},
    "manager1": {"password": "admin123", "role": "manager"}
}

products = {
    "SKU001": {"name": "Apple", "price": 1.00, "stock": 100},
    "SKU002": {"name": "Banana", "price": 0.50, "stock": 150},
    "SKU003": {"name": "Orange", "price": 1.20, "stock": 80}
}

sales_transactions = [] # To store completed sales

# --- Helper Functions ---
def login_required(role=None):
    def wrapper(fn):
        def decorated_view(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                return jsonify({"message": "Unauthorized: Login required"}), 401
            if role and session.get('role') != role:
                return jsonify({"message": f"Forbidden: {role} role required"}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- Routes ---

@app.route('/')
def home():
    return "Welcome to the Cashier App API!"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = users.get(username)
    if user and user['password'] == password:
        session['logged_in'] = True
        session['username'] = username
        session['role'] = user['role']
        return jsonify({"message": "Login successful", "role": user['role']}), 200
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/logout', methods=['POST'])
@login_required()
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('role', None)
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/sales/process', methods=['POST'])
@login_required(role='cashier')
def process_sale():
    data = request.get_json()
    items = data.get('items') # [{'sku': 'SKU001', 'quantity': 2}]

    if not items:
        return jsonify({"message": "No items provided for sale"}), 400

    total_amount = 0
    processed_items = []
    for item in items:
        sku = item.get('sku')
        quantity = item.get('quantity')
        product = products.get(sku)

        if not product:
            return jsonify({"message": f"Product with SKU {sku} not found"}), 404
        if product['stock'] < quantity:
            return jsonify({"message": f"Insufficient stock for {product['name']}. Available: {product['stock']}"}), 400

        item_total = product['price'] * quantity
        total_amount += item_total
        product['stock'] -= quantity # Update stock
        processed_items.append({"sku": sku, "name": product['name'], "quantity": quantity, "price_per_unit": product['price'], "item_total": item_total})

    transaction = {
        "transaction_id": len(sales_transactions) + 1,
        "cashier": session.get('username'),
        "items": processed_items,
        "total_amount": total_amount,
        "timestamp": os.getenv('FLASK_ENV', 'development') # Placeholder for a real timestamp
    }
    sales_transactions.append(transaction)

    return jsonify({"message": "Sale processed successfully", "transaction": transaction}), 200

@app.route('/inventory', methods=['GET'])
@login_required(role='manager')
def get_inventory():
    return jsonify(products), 200

@app.route('/inventory/add', methods=['POST'])
@login_required(role='manager')
def add_product():
    data = request.get_json()
    sku = data.get('sku')
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')

    if not all([sku, name, price, stock]):
        return jsonify({"message": "Missing product information"}), 400

    if sku in products:
        return jsonify({"message": f"Product with SKU {sku} already exists"}), 409

    products[sku] = {"name": name, "price": price, "stock": stock}
    return jsonify({"message": "Product added successfully", "product": products[sku]}), 201

@app.route('/inventory/update/<sku>', methods=['PUT'])
@login_required(role='manager')
def update_product_stock(sku):
    data = request.get_json()
    new_stock = data.get('stock')

    if sku not in products:
        return jsonify({"message": f"Product with SKU {sku} not found"}), 404
    if new_stock is None or not isinstance(new_stock, int) or new_stock < 0:
        return jsonify({"message": "Invalid stock value"}), 400

    products[sku]['stock'] = new_stock
    return jsonify({"message": "Product stock updated successfully", "product": products[sku]}), 200

@app.route('/reports/sales', methods=['GET'])
@login_required(role='manager')
def get_sales_report():
    return jsonify(sales_transactions), 200

if __name__ == '__main__':
    # For a real application, consider using a WSGI server like Gunicorn
    app.run(debug=True) # debug=True should not be used in production
