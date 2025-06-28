from flask import Flask, request, jsonify
import json
import sqlite3 # For a simple demo database

app = Flask(__name__, static_folder='.', static_url_path='')

# --- Database Setup (Simple Demo) ---
DB_NAME = 'sample_data.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Drop tables if they exist to ensure a clean state for the demo
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS products")
    cursor.execute("DROP TABLE IF EXISTS orders")

    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE
        )
    ''')
    # Create products table
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL
        )
    ''')
    # Create orders table
    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            order_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Insert sample data
    users_data = [
        (1, 'Alice Smith', 'alice@example.com'),
        (2, 'Bob Johnson', 'bob@example.com'),
        (3, 'Charlie Brown', 'charlie@example.com')
    ]
    products_data = [
        (101, 'Laptop', 'Electronics', 1200.00),
        (102, 'Mouse', 'Electronics', 25.00),
        (103, 'Keyboard', 'Electronics', 75.00),
        (201, 'T-shirt', 'Apparel', 20.00),
        (202, 'Jeans', 'Apparel', 50.00)
    ]
    orders_data = [
        (1, 1, 101, 1, '2023-01-15'),
        (2, 1, 102, 2, '2023-01-15'),
        (3, 2, 201, 5, '2023-01-20'),
        (4, 3, 103, 1, '2023-01-22'),
        (5, 2, 101, 1, '2023-02-01')
    ]
    cursor.executemany("INSERT INTO users VALUES (?,?,?)", users_data)
    cursor.executemany("INSERT INTO products VALUES (?,?,?,?)", products_data)
    cursor.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", orders_data)
    conn.commit()
    conn.close()

# --- NLP to SQL (Very Basic Placeholder) ---
def convert_text_to_sql(text):
    """
    This is a highly simplified placeholder.
    In a real application, this would involve sophisticated NLP techniques.
    """
    text_lower = text.lower()
    sql_query = f"-- Placeholder: Could not determine SQL for: {text}"

    # Example simple mappings
    if "show all users" in text_lower or "list users" in text_lower:
        sql_query = "SELECT id, name, email FROM users;"
    elif "show all products" in text_lower or "list products" in text_lower:
        sql_query = "SELECT id, name, category, price FROM products;"
    elif "show all orders" in text_lower or "list orders" in text_lower:
        sql_query = "SELECT id, user_id, product_id, quantity, order_date FROM orders;"
    elif "how many users" in text_lower:
        sql_query = "SELECT COUNT(*) AS total_users FROM users;"
    elif "products in electronics" in text_lower:
        sql_query = "SELECT id, name, price FROM products WHERE category = 'Electronics';"
    elif "orders by alice" in text_lower: # Assumes Alice is user_id 1
        sql_query = """
            SELECT o.id, p.name AS product_name, o.quantity, o.order_date
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN products p ON o.product_id = p.id
            WHERE u.name LIKE 'Alice%';
        """
    # Add more rudimentary rules here

    return sql_query

# --- Database Interaction ---
def execute_sql_query(sql_query):
    """
    Executes the given SQL query and returns the results.
    Returns column names and rows.
    """
    if sql_query.startswith("-- Placeholder:") or not sql_query.strip():
        return [], f"Query not executed: {sql_query}"

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    cursor = conn.cursor()
    results = []
    error_message = None

    try:
        cursor.execute(sql_query)
        # For SELECT queries, fetch results
        if sql_query.strip().upper().startswith("SELECT"):
            column_names = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            for row in rows:
                results.append(dict(zip(column_names, row)))
        else: # For INSERT, UPDATE, DELETE, etc.
            conn.commit()
            results = [{"status": "success", "rows_affected": cursor.rowcount}]

    except sqlite3.Error as e:
        error_message = f"Database error: {e}"
        app.logger.error(f"Database error: {e} for query: {sql_query}")
    finally:
        conn.close()

    return results, error_message


@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/process_query', methods=['POST'])
def process_query():
    try:
        data = request.get_json()
        if not data or 'query_text' not in data:
            return jsonify({"error": "Missing 'query_text' in request"}), 400

        user_text = data['query_text']
        app.logger.info(f"Received text: {user_text}")

        # 1. Convert text to SQL (Placeholder)
        sql_query = convert_text_to_sql(user_text)
        app.logger.info(f"Generated SQL: {sql_query}")

        # 2. Execute SQL query (Placeholder)
        table_data, db_error = execute_sql_query(sql_query)

        if db_error:
            app.logger.error(f"DB Error: {db_error}")
            # Return the error to the frontend so it can be displayed
            return jsonify({
                "sql_query": sql_query,
                "result_table": [],
                "error": db_error
            }), 200 # Return 200 so front-end can parse it, error is in the payload

        app.logger.info(f"Query results: {json.dumps(table_data, indent=2)}")

        return jsonify({
            "sql_query": sql_query,
            "result_table": table_data
        })

    except Exception as e:
        app.logger.error(f"Error in /process_query: {e}")
        return jsonify({"error": str(e), "detail": "An internal server error occurred."}), 500

if __name__ == '__main__':
    init_db() # Initialize the database with schema and sample data
    app.run(debug=True, port=5001) # Running on a different port just in case 5000 is in use
