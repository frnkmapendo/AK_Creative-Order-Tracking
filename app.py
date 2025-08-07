from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'ak_creative_secret_key_2025'

# Database setup
DATABASE = 'ak_creative.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    
    # Create orders table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            description TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price_tzs REAL NOT NULL,
            total_amount_tzs REAL NOT NULL,
            total_amount_usd REAL,
            payment_received TEXT NOT NULL DEFAULT 'No',
            order_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create transactions table for Income & Expenses
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('Sales', 'Expenses')),
            amount_tzs REAL NOT NULL,
            amount_usd REAL,
            transaction_date DATE NOT NULL,
            order_id INTEGER,
            is_auto_generated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Currency conversion rate (approximate)
USD_TO_TZS_RATE = 2500

def convert_currency(amount, from_currency='TZS'):
    """Convert between TZS and USD"""
    if from_currency == 'TZS':
        return round(amount / USD_TO_TZS_RATE, 2)
    else:  # USD to TZS
        return round(amount * USD_TO_TZS_RATE, 2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/orders')
def orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('orders.html', orders=orders)

@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        item_type = request.form['item_type']
        description = request.form['description']
        quantity = int(request.form['quantity'])
        unit_price_tzs = float(request.form['unit_price_tzs'])
        payment_received = request.form['payment_received']
        order_date = request.form['order_date']
        
        total_amount_tzs = quantity * unit_price_tzs
        total_amount_usd = convert_currency(total_amount_tzs)
        
        conn = get_db_connection()
        cursor = conn.execute('''
            INSERT INTO orders (customer_name, item_type, description, quantity, 
                               unit_price_tzs, total_amount_tzs, total_amount_usd, 
                               payment_received, order_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_name, item_type, description, quantity, unit_price_tzs, 
              total_amount_tzs, total_amount_usd, payment_received, order_date))
        
        order_id = cursor.lastrowid
        
        # If payment is received, auto-generate sales transaction
        if payment_received == 'Yes':
            conn.execute('''
                INSERT INTO transactions (description, category, amount_tzs, amount_usd, 
                                        transaction_date, order_id, is_auto_generated)
                VALUES (?, 'Sales', ?, ?, ?, ?, TRUE)
            ''', (item_type, total_amount_tzs, total_amount_usd, order_date, order_id))
        
        conn.commit()
        conn.close()
        
        flash('Order added successfully!')
        return redirect(url_for('orders'))
    
    return render_template('add_order.html')

@app.route('/income_expenses')
def income_expenses():
    conn = get_db_connection()
    transactions = conn.execute('''
        SELECT t.*, o.customer_name 
        FROM transactions t
        LEFT JOIN orders o ON t.order_id = o.id
        ORDER BY t.transaction_date DESC, t.created_at DESC
    ''').fetchall()
    
    # Calculate totals
    total_sales_tzs = 0
    total_expenses_tzs = 0
    
    for transaction in transactions:
        if transaction['category'] == 'Sales':
            total_sales_tzs += transaction['amount_tzs']
        else:
            total_expenses_tzs += transaction['amount_tzs']
    
    total_sales_usd = convert_currency(total_sales_tzs)
    total_expenses_usd = convert_currency(total_expenses_tzs)
    net_income_tzs = total_sales_tzs - total_expenses_tzs
    net_income_usd = convert_currency(net_income_tzs)
    
    conn.close()
    
    return render_template('income_expenses.html', 
                         transactions=transactions,
                         total_sales_tzs=total_sales_tzs,
                         total_sales_usd=total_sales_usd,
                         total_expenses_tzs=total_expenses_tzs,
                         total_expenses_usd=total_expenses_usd,
                         net_income_tzs=net_income_tzs,
                         net_income_usd=net_income_usd)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount_tzs = float(request.form['amount_tzs'])
        transaction_date = request.form['transaction_date']
        
        amount_usd = convert_currency(amount_tzs)
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO transactions (description, category, amount_tzs, amount_usd, 
                                    transaction_date, is_auto_generated)
            VALUES (?, 'Expenses', ?, ?, ?, FALSE)
        ''', (description, amount_tzs, amount_usd, transaction_date))
        conn.commit()
        conn.close()
        
        flash('Expense added successfully!')
        return redirect(url_for('income_expenses'))
    
    return render_template('add_expense.html')

@app.route('/update_payment/<int:order_id>')
def update_payment(order_id):
    """Update payment status and auto-generate sales transaction"""
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if order and order['payment_received'] == 'No':
        # Update payment status
        conn.execute('UPDATE orders SET payment_received = ? WHERE id = ?', ('Yes', order_id))
        
        # Create auto-generated sales transaction
        conn.execute('''
            INSERT INTO transactions (description, category, amount_tzs, amount_usd, 
                                    transaction_date, order_id, is_auto_generated)
            VALUES (?, 'Sales', ?, ?, ?, ?, TRUE)
        ''', (order['item_type'], order['total_amount_tzs'], order['total_amount_usd'], 
              order['order_date'], order_id))
        
        conn.commit()
        flash('Payment status updated and sales transaction created!')
    
    conn.close()
    return redirect(url_for('orders'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)