#!/usr/bin/env python3
"""
AK Creative Order Tracker - Geometry Management Fixed
User: frnkmapendo
Current Date: 2025-08-07 11:05:23 UTC
Fixed: Geometry manager conflicts between grid and pack
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
import os
import sys
from datetime import datetime, date
import calendar
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

# Try to import tkcalendar, fallback to basic date entry if not available
try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

# Application Constants
APP_NAME = "AK Creative Order Tracker"
APP_VERSION = "1.1.2"
AUTHOR = "frnkmapendo"
BUSINESS_NAME = "AK Creative"
CREATED_DATE = "2025-08-07 11:05:23 UTC"

# Currency and Business Constants
PRIMARY_CURRENCY = "TZS"
SECONDARY_CURRENCY = "USD"
DEFAULT_EXCHANGE_RATE = 2300  # TZS to USD approximate rate

# Product/Service categories for AK Creative
PRODUCT_CATEGORIES = [
    "Picha", "Banner", "Holder", "Notebook", "Poster", "Sticker", 
    "Design", "Frame A4", "Frame A3", "Cup", "Game", 
    "Picha Mbao A3", "Picha Mbao A4", "Picha Mbao A2", "Gold Strip"
]

# Updated Description Items for Income & Expenses
DESCRIPTION_ITEMS = [
    "Picha", "Banner", "Holder", "Notebook", "Poster", "Sticker",
    "Design", "Transport", "Meals", "Office Supplies", "Rent", 
    "Salaries", "Electricity", "Water", "Internet", "Security", "Trash"
]

# Updated Categories - Only Sales and Expenses
TRANSACTION_CATEGORIES = ["Sales", "Expenses"]

@dataclass
class Order:
    """Order data class matching AK Creative Excel format"""
    id: Optional[int] = None
    date: str = ""
    customer_name: str = ""
    product_service: str = ""
    quantity: int = 0
    unit_price_tzs: float = 0.0
    total_cost_tzs: float = 0.0
    paid_amount: float = 0.0
    pending_amount: float = 0.0
    payment_received: str = "No"
    payment_method: str = ""
    delivery_status: str = "Pending"
    notes: str = ""
    phone_number: str = ""
    created_at: str = ""
    updated_at: str = ""

@dataclass
class Transaction:
    """Income & Expense transaction data class"""
    id: Optional[int] = None
    date: str = ""
    description: str = ""
    category: str = ""  # "Sales" or "Expenses"
    income_tzs: float = 0.0
    income_usd: float = 0.0
    expense_tzs: float = 0.0
    expense_usd: float = 0.0
    payment_method: str = ""
    notes: str = ""
    order_id: Optional[int] = None  # Link to order for auto-generated sales
    is_auto_generated: bool = False  # Flag for auto-generated entries
    created_at: str = ""

class Database:
    """Database manager for AK Creative Order Tracker"""
    
    def __init__(self, db_path="ak_creative.db"):
        self.db_path = db_path
        self.initialize()
    
    def initialize(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    customer_name TEXT NOT NULL,
                    product_service TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price_tzs REAL NOT NULL,
                    total_cost_tzs REAL NOT NULL,
                    paid_amount REAL DEFAULT 0,
                    pending_amount REAL DEFAULT 0,
                    payment_received TEXT DEFAULT 'No',
                    payment_method TEXT,
                    delivery_status TEXT DEFAULT 'Pending',
                    notes TEXT,
                    phone_number TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    income_tzs REAL DEFAULT 0,
                    income_usd REAL DEFAULT 0,
                    expense_tzs REAL DEFAULT 0,
                    expense_usd REAL DEFAULT 0,
                    payment_method TEXT,
                    notes TEXT,
                    order_id INTEGER,
                    is_auto_generated BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (id)
                )
            ''')
            
            # Check if new columns exist, add them if not
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'order_id' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN order_id INTEGER')
            if 'is_auto_generated' not in columns:
                cursor.execute('ALTER TABLE transactions ADD COLUMN is_auto_generated BOOLEAN DEFAULT 0')
            
            conn.commit()
    
    def create_order(self, order: Order) -> int:
        """Create a new order and auto-generate sales transaction if paid"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (date, customer_name, product_service, quantity, 
                                   unit_price_tzs, total_cost_tzs, paid_amount, pending_amount,
                                   payment_received, payment_method, delivery_status, notes, phone_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.date, order.customer_name, order.product_service, order.quantity,
                order.unit_price_tzs, order.total_cost_tzs, order.paid_amount, order.pending_amount,
                order.payment_received, order.payment_method, order.delivery_status, 
                order.notes, order.phone_number
            ))
            
            order_id = cursor.lastrowid
            
            # Auto-generate sales transaction if payment received
            if order.payment_received == "Yes" and order.paid_amount > 0:
                self._create_auto_sales_transaction(cursor, order_id, order)
            
            return order_id
    
    def _create_auto_sales_transaction(self, cursor, order_id: int, order: Order):
        """Create auto-generated sales transaction for paid order"""
        usd_amount = order.paid_amount / DEFAULT_EXCHANGE_RATE
        
        cursor.execute('''
            INSERT INTO transactions (date, description, category, income_tzs, income_usd,
                                    expense_tzs, expense_usd, payment_method, notes, 
                                    order_id, is_auto_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order.date, order.product_service, "Sales", order.paid_amount, usd_amount,
            0, 0, order.payment_method, f"Auto-generated from Order #{order_id} - {order.customer_name}",
            order_id, True
        ))
    
    def update_order(self, order_id: int, order: Order):
        """Update an existing order and handle sales transaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE orders 
                SET date=?, customer_name=?, product_service=?, quantity=?, 
                    unit_price_tzs=?, total_cost_tzs=?, paid_amount=?, pending_amount=?,
                    payment_received=?, payment_method=?, delivery_status=?, notes=?, 
                    phone_number=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (
                order.date, order.customer_name, order.product_service, order.quantity,
                order.unit_price_tzs, order.total_cost_tzs, order.paid_amount, order.pending_amount,
                order.payment_received, order.payment_method, order.delivery_status,
                order.notes, order.phone_number, order_id
            ))
            
            # Remove existing auto-generated transaction for this order
            cursor.execute('DELETE FROM transactions WHERE order_id=? AND is_auto_generated=1', (order_id,))
            
            # Create new auto-generated transaction if payment received
            if order.payment_received == "Yes" and order.paid_amount > 0:
                self._create_auto_sales_transaction(cursor, order_id, order)
    
    def get_all_orders(self) -> List[Order]:
        """Get all orders"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders ORDER BY date DESC, id DESC')
            rows = cursor.fetchall()
            
            orders = []
            for row in rows:
                order = Order(
                    id=row[0], date=row[1], customer_name=row[2], product_service=row[3],
                    quantity=row[4], unit_price_tzs=row[5], total_cost_tzs=row[6],
                    paid_amount=row[7], pending_amount=row[8], payment_received=row[9],
                    payment_method=row[10], delivery_status=row[11], notes=row[12],
                    phone_number=row[13], created_at=row[14], updated_at=row[15]
                )
                orders.append(order)
            
            return orders
    
    def delete_order(self, order_id: int):
        """Delete an order and its auto-generated transactions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions WHERE order_id=? AND is_auto_generated=1', (order_id,))
            cursor.execute('DELETE FROM orders WHERE id=?', (order_id,))
    
    def create_transaction(self, transaction: Transaction) -> int:
        """Create a new transaction"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions (date, description, category, income_tzs, income_usd,
                                        expense_tzs, expense_usd, payment_method, notes, 
                                        order_id, is_auto_generated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction.date, transaction.description, transaction.category,
                transaction.income_tzs, transaction.income_usd, transaction.expense_tzs,
                transaction.expense_usd, transaction.payment_method, transaction.notes,
                transaction.order_id, transaction.is_auto_generated
            ))
            return cursor.lastrowid
    
    def delete_transaction(self, transaction_id: int):
        """Delete a transaction by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM transactions WHERE id=?', (transaction_id,))
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all transactions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM transactions ORDER BY date DESC, id DESC')
            rows = cursor.fetchall()
            
            transactions = []
            for row in rows:
                if len(row) >= 12:  # New schema
                    transaction = Transaction(
                        id=row[0], date=row[1], description=row[2], category=row[3],
                        income_tzs=row[4], income_usd=row[5], expense_tzs=row[6],
                        expense_usd=row[7], payment_method=row[8], notes=row[9],
                        order_id=row[10], is_auto_generated=bool(row[11]), created_at=row[12]
                    )
                else:  # Old schema
                    transaction = Transaction(
                        id=row[0], date=row[1], description=row[2], category=row[3],
                        income_tzs=row[4], income_usd=row[5], expense_tzs=row[6],
                        expense_usd=row[7], payment_method=row[8], notes=row[9],
                        created_at=row[10]
                    )
                transactions.append(transaction)
            
            return transactions
    
    def get_monthly_summary(self, month: int, year: int) -> Dict:
        """Get monthly financial summary"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get date range for the month
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"
            
            # Get income (sales) from transactions
            cursor.execute('''
                SELECT SUM(income_tzs), SUM(income_usd) FROM transactions 
                WHERE date BETWEEN ? AND ? AND category = 'Sales'
            ''', (start_date, end_date))
            income_data = cursor.fetchone()
            total_income_tzs = income_data[0] or 0
            total_income_usd = income_data[1] or 0
            
            # Get expenses from transactions
            cursor.execute('''
                SELECT SUM(expense_tzs), SUM(expense_usd) FROM transactions 
                WHERE date BETWEEN ? AND ? AND category = 'Expenses'
            ''', (start_date, end_date))
            expense_data = cursor.fetchone()
            total_expense_tzs = expense_data[0] or 0
            total_expense_usd = expense_data[1] or 0
            
            # Calculate net profit
            net_profit_tzs = total_income_tzs - total_expense_tzs
            net_profit_usd = total_income_usd - total_expense_usd
            
            return {
                'month': month,
                'year': year,
                'total_income_tzs': total_income_tzs,
                'total_income_usd': total_income_usd,
                'total_expense_tzs': total_expense_tzs,
                'total_expense_usd': total_expense_usd,
                'net_profit_tzs': net_profit_tzs,
                'net_profit_usd': net_profit_usd
            }

class SimpleDate:
    """Simple date picker fallback"""
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        
        today = date.today()
        self.year_var = tk.StringVar(value=str(today.year))
        self.month_var = tk.StringVar(value=str(today.month))
        self.day_var = tk.StringVar(value=str(today.day))
        
        ttk.Label(self.frame, text="Year:").pack(side=tk.LEFT)
        year_combo = ttk.Combobox(self.frame, textvariable=self.year_var, 
                                 values=[str(i) for i in range(2020, 2030)], width=6)
        year_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.frame, text="Month:").pack(side=tk.LEFT, padx=(10, 0))
        month_combo = ttk.Combobox(self.frame, textvariable=self.month_var,
                                  values=[str(i) for i in range(1, 13)], width=4)
        month_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.frame, text="Day:").pack(side=tk.LEFT, padx=(10, 0))
        day_combo = ttk.Combobox(self.frame, textvariable=self.day_var,
                                values=[str(i) for i in range(1, 32)], width=4)
        day_combo.pack(side=tk.LEFT, padx=2)
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        self.frame.grid(**kwargs)
    
    def get_date(self):
        try:
            year = int(self.year_var.get())
            month = int(self.month_var.get())
            day = int(self.day_var.get())
            return date(year, month, day)
        except:
            return date.today()
    
    def set_date(self, date_obj):
        self.year_var.set(str(date_obj.year))
        self.month_var.set(str(date_obj.month))
        self.day_var.set(str(date_obj.day))

class OrderForm:
    """Order form with FIXED geometry management - using only PACK"""
    
    def __init__(self, parent, on_save_callback):
        self.parent = parent
        self.on_save_callback = on_save_callback
        self.current_order_id = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create widgets using only PACK geometry manager"""
        
        # Create main container with scrollable frame
        canvas = tk.Canvas(self.parent)
        scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Date field
        date_frame = ttk.Frame(self.scrollable_frame)
        date_frame.pack(fill=tk.X, pady=5)
        ttk.Label(date_frame, text="Date:*", width=18).pack(side=tk.LEFT)
        if HAS_CALENDAR:
            self.order_date = DateEntry(date_frame, width=25, background='darkblue',
                                       foreground='white', borderwidth=2, date_pattern='dd/mm/yyyy')
        else:
            self.order_date = SimpleDate(date_frame)
        self.order_date.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Customer Name
        customer_frame = ttk.Frame(self.scrollable_frame)
        customer_frame.pack(fill=tk.X, pady=5)
        ttk.Label(customer_frame, text="Customer Name:*", width=18).pack(side=tk.LEFT)
        self.customer_name_var = tk.StringVar()
        ttk.Entry(customer_frame, textvariable=self.customer_name_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Phone Number
        phone_frame = ttk.Frame(self.scrollable_frame)
        phone_frame.pack(fill=tk.X, pady=5)
        ttk.Label(phone_frame, text="Phone Number:", width=18).pack(side=tk.LEFT)
        self.phone_var = tk.StringVar()
        ttk.Entry(phone_frame, textvariable=self.phone_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Product/Service
        product_frame = ttk.Frame(self.scrollable_frame)
        product_frame.pack(fill=tk.X, pady=5)
        ttk.Label(product_frame, text="Product/Service:*", width=18).pack(side=tk.LEFT)
        self.product_var = tk.StringVar()
        product_combo = ttk.Combobox(product_frame, textvariable=self.product_var, values=PRODUCT_CATEGORIES)
        product_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Quantity
        quantity_frame = ttk.Frame(self.scrollable_frame)
        quantity_frame.pack(fill=tk.X, pady=5)
        ttk.Label(quantity_frame, text="Quantity:*", width=18).pack(side=tk.LEFT)
        self.quantity_var = tk.StringVar()
        quantity_entry = ttk.Entry(quantity_frame, textvariable=self.quantity_var)
        quantity_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        quantity_entry.bind('<KeyRelease>', self.calculate_total)
        
        # Unit Price (TZS)
        price_frame = ttk.Frame(self.scrollable_frame)
        price_frame.pack(fill=tk.X, pady=5)
        ttk.Label(price_frame, text="Unit Price (TZS):*", width=18).pack(side=tk.LEFT)
        self.unit_price_var = tk.StringVar()
        price_entry = ttk.Entry(price_frame, textvariable=self.unit_price_var)
        price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        price_entry.bind('<KeyRelease>', self.calculate_total)
        
        # Total Cost (TZS) - Auto calculated
        total_frame = ttk.Frame(self.scrollable_frame)
        total_frame.pack(fill=tk.X, pady=5)
        ttk.Label(total_frame, text="Total Cost (TZS):", width=18).pack(side=tk.LEFT)
        self.total_cost_var = tk.StringVar()
        ttk.Entry(total_frame, textvariable=self.total_cost_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Paid Amount
        paid_frame = ttk.Frame(self.scrollable_frame)
        paid_frame.pack(fill=tk.X, pady=5)
        ttk.Label(paid_frame, text="Paid Amount:", width=18).pack(side=tk.LEFT)
        self.paid_amount_var = tk.StringVar()
        paid_entry = ttk.Entry(paid_frame, textvariable=self.paid_amount_var)
        paid_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        paid_entry.bind('<KeyRelease>', self.calculate_pending)
        
        # Pending Amount - Auto calculated
        pending_frame = ttk.Frame(self.scrollable_frame)
        pending_frame.pack(fill=tk.X, pady=5)
        ttk.Label(pending_frame, text="Pending Amount:", width=18).pack(side=tk.LEFT)
        self.pending_amount_var = tk.StringVar()
        ttk.Entry(pending_frame, textvariable=self.pending_amount_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Payment Received
        payment_received_frame = ttk.Frame(self.scrollable_frame)
        payment_received_frame.pack(fill=tk.X, pady=5)
        ttk.Label(payment_received_frame, text="Payment Received:*", width=18).pack(side=tk.LEFT)
        self.payment_received_var = tk.StringVar(value="No")
        payment_combo = ttk.Combobox(payment_received_frame, textvariable=self.payment_received_var,
                                    values=["Yes", "No"], state="readonly")
        payment_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Payment Method
        method_frame = ttk.Frame(self.scrollable_frame)
        method_frame.pack(fill=tk.X, pady=5)
        ttk.Label(method_frame, text="Payment Method:", width=18).pack(side=tk.LEFT)
        self.payment_method_var = tk.StringVar()
        method_combo = ttk.Combobox(method_frame, textvariable=self.payment_method_var,
                                   values=["Cash", "M-Pesa", "Bank Transfer", "Tigo Pesa", "Airtel Money"])
        method_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Delivery Status
        delivery_frame = ttk.Frame(self.scrollable_frame)
        delivery_frame.pack(fill=tk.X, pady=5)
        ttk.Label(delivery_frame, text="Delivery Status:*", width=18).pack(side=tk.LEFT)
        self.delivery_status_var = tk.StringVar(value="Pending")
        status_combo = ttk.Combobox(delivery_frame, textvariable=self.delivery_status_var,
                                   values=["Pending", "Pick Up", "Delivered", "In Progress"], state="readonly")
        status_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Notes
        notes_frame = ttk.Frame(self.scrollable_frame)
        notes_frame.pack(fill=tk.X, pady=5)
        ttk.Label(notes_frame, text="Notes:", width=18).pack(side=tk.LEFT, anchor="n")
        self.notes_text = tk.Text(notes_frame, height=4, width=30)
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Buttons
        buttons_frame = ttk.Frame(self.scrollable_frame)
        buttons_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(buttons_frame, text="💾 Save Order", command=self.save_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="🗑️ Clear Form", command=self.clear_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="❌ Delete Order", command=self.delete_order).pack(side=tk.LEFT, padx=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def calculate_total(self, event=None):
        """Calculate total cost automatically"""
        try:
            quantity = float(self.quantity_var.get() or 0)
            unit_price = float(self.unit_price_var.get() or 0)
            total = quantity * unit_price
            self.total_cost_var.set(f"{total:,.0f}")
            self.calculate_pending()
        except ValueError:
            self.total_cost_var.set("0")
    
    def calculate_pending(self, event=None):
        """Calculate pending amount automatically"""
        try:
            total_cost = float(self.total_cost_var.get().replace(',', '') or 0)
            paid_amount = float(self.paid_amount_var.get() or 0)
            pending = total_cost - paid_amount
            self.pending_amount_var.set(f"{pending:,.0f}")
        except ValueError:
            self.pending_amount_var.set("0")
    
    def save_order(self):
        """Save the current order"""
        if not self.validate_form():
            return
        
        order = Order(
            date=self.order_date.get_date().strftime('%d/%m/%Y'),
            customer_name=self.customer_name_var.get().strip(),
            phone_number=self.phone_var.get().strip(),
            product_service=self.product_var.get().strip(),
            quantity=int(self.quantity_var.get()),
            unit_price_tzs=float(self.unit_price_var.get()),
            total_cost_tzs=float(self.total_cost_var.get().replace(',', '')),
            paid_amount=float(self.paid_amount_var.get() or 0),
            pending_amount=float(self.pending_amount_var.get().replace(',', '') or 0),
            payment_received=self.payment_received_var.get(),
            payment_method=self.payment_method_var.get(),
            delivery_status=self.delivery_status_var.get(),
            notes=self.notes_text.get("1.0", tk.END).strip()
        )
        
        if self.current_order_id:
            order.id = self.current_order_id
        
        self.on_save_callback(order)
    
    def validate_form(self):
        """Validate form data"""
        if not self.customer_name_var.get().strip():
            messagebox.showerror("Validation Error", "Customer name is required!")
            return False
        
        if not self.product_var.get().strip():
            messagebox.showerror("Validation Error", "Product/Service is required!")
            return False
        
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            messagebox.showerror("Validation Error", "Please enter a valid quantity!")
            return False
        
        try:
            unit_price = float(self.unit_price_var.get())
            if unit_price <= 0:
                raise ValueError("Unit price must be positive")
        except ValueError:
            messagebox.showerror("Validation Error", "Please enter a valid unit price!")
            return False
        
        return True
    
    def clear_form(self):
        """Clear all form fields"""
        self.current_order_id = None
        if hasattr(self.order_date, 'set_date'):
            self.order_date.set_date(date.today())
        self.customer_name_var.set("")
        self.phone_var.set("")
        self.product_var.set("")
        self.quantity_var.set("")
        self.unit_price_var.set("")
        self.total_cost_var.set("")
        self.paid_amount_var.set("")
        self.pending_amount_var.set("")
        self.payment_received_var.set("No")
        self.payment_method_var.set("")
        self.delivery_status_var.set("Pending")
        self.notes_text.delete("1.0", tk.END)
    
    def load_order(self, order: Order):
        """Load order data into form"""
        self.clear_form()
        self.current_order_id = order.id
        
        # Handle date
        if order.date:
            try:
                order_date = datetime.strptime(order.date, '%d/%m/%Y').date()
                if hasattr(self.order_date, 'set_date'):
                    self.order_date.set_date(order_date)
            except:
                pass
        
        self.customer_name_var.set(order.customer_name)
        self.phone_var.set(order.phone_number)
        self.product_var.set(order.product_service)
        self.quantity_var.set(str(order.quantity))
        self.unit_price_var.set(str(order.unit_price_tzs))
        self.total_cost_var.set(f"{order.total_cost_tzs:,.0f}")
        self.paid_amount_var.set(str(order.paid_amount))
        self.pending_amount_var.set(f"{order.pending_amount:,.0f}")
        self.payment_received_var.set(order.payment_received)
        self.payment_method_var.set(order.payment_method)
        self.delivery_status_var.set(order.delivery_status)
        self.notes_text.insert("1.0", order.notes)
    
    def delete_order(self):
        """Delete current order"""
        if not self.current_order_id:
            messagebox.showwarning("Warning", "No order selected to delete!")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this order?"):
            self.on_save_callback(Order(id=self.current_order_id), delete=True)

class OrderList:
    """Order list widget with proper pack geometry"""
    
    def __init__(self, parent, on_select_callback):
        self.parent = parent
        self.on_select_callback = on_select_callback
        self.orders = []
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create widgets using only PACK geometry manager"""
        
        # Search and filter frame
        controls_frame = ttk.Frame(self.parent)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Search
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))
        search_entry.bind('<KeyRelease>', self.on_search)
        
        # Payment filter
        ttk.Label(search_frame, text="Payment:").pack(side=tk.LEFT)
        self.payment_filter_var = tk.StringVar(value="All")
        payment_filter = ttk.Combobox(search_frame, textvariable=self.payment_filter_var,
                                     values=["All", "Yes", "No"], width=10)
        payment_filter.pack(side=tk.LEFT, padx=(5, 10))
        payment_filter.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        # Delivery filter
        ttk.Label(search_frame, text="Delivery:").pack(side=tk.LEFT)
        self.delivery_filter_var = tk.StringVar(value="All")
        delivery_filter = ttk.Combobox(search_frame, textvariable=self.delivery_filter_var,
                                      values=["All", "Pending", "Pick Up", "Delivered", "In Progress"], width=12)
        delivery_filter.pack(side=tk.LEFT, padx=(5, 10))
        delivery_filter.bind('<<ComboboxSelected>>', self.on_filter_change)
        
        ttk.Button(controls_frame, text="🔄 Refresh", command=self.refresh).pack(side=tk.RIGHT)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(self.parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Date', 'Customer', 'Product', 'Qty', 'Price', 'Total', 'Paid', 'Pending', 'Payment', 'Delivery', 'Phone')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        column_widths = {'ID': 50, 'Date': 80, 'Customer': 120, 'Product': 100, 'Qty': 50, 
                        'Price': 80, 'Total': 100, 'Paid': 80, 'Pending': 80, 'Payment': 80, 'Delivery': 80, 'Phone': 100}
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), minwidth=50)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack everything
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self.on_item_select)
        
        # Status bar
        self.status_bar = ttk.Label(self.parent, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
    
    def refresh(self, orders=None):
        """Refresh the order list"""
        if orders is not None:
            self.orders = orders
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Apply filters
        filtered_orders = self.apply_filters(self.orders)
        
        # Calculate totals
        total_revenue = sum(order.total_cost_tzs for order in filtered_orders)
        total_paid = sum(order.paid_amount for order in filtered_orders)
        total_pending = sum(order.pending_amount for order in filtered_orders)
        
        # Insert orders
        for order in filtered_orders:
            # Color coding
            item_tags = []
            if order.payment_received == "No":
                item_tags.append("unpaid")
            elif order.payment_received == "Yes":
                item_tags.append("paid")
            
            if order.delivery_status == "Pending":
                item_tags.append("pending_delivery")
            
            self.tree.insert('', tk.END, values=(
                order.id, order.date, order.customer_name, order.product_service,
                order.quantity, f"{order.unit_price_tzs:,.0f}", f"{order.total_cost_tzs:,.0f}",
                f"{order.paid_amount:,.0f}", f"{order.pending_amount:,.0f}",
                order.payment_received, order.delivery_status, order.phone_number
            ), tags=item_tags)
        
        # Configure tags for color coding
        self.tree.tag_configure("unpaid", background="#ffebee")
        self.tree.tag_configure("paid", background="#e8f5e8")
        self.tree.tag_configure("pending_delivery", foreground="#d32f2f")
        
        # Update status bar
        self.status_bar.config(text=f"Orders: {len(filtered_orders)} | Total Revenue: TZS {total_revenue:,.0f} | Paid: TZS {total_paid:,.0f} | Pending: TZS {total_pending:,.0f}")
    
    def apply_filters(self, orders):
        """Apply search and filters"""
        filtered_orders = orders
        
        # Search filter
        search_term = self.search_var.get().lower()
        if search_term:
            filtered_orders = [
                order for order in filtered_orders
                if (search_term in order.customer_name.lower() or
                    search_term in order.product_service.lower() or
                    search_term in str(order.id) or
                    search_term in order.phone_number.lower())
            ]
        
        # Payment filter
        payment_filter = self.payment_filter_var.get()
        if payment_filter != "All":
            filtered_orders = [
                order for order in filtered_orders
                if order.payment_received == payment_filter
            ]
        
        # Delivery filter
        delivery_filter = self.delivery_filter_var.get()
        if delivery_filter != "All":
            filtered_orders = [
                order for order in filtered_orders
                if order.delivery_status == delivery_filter
            ]
        
        return filtered_orders
    
    def on_search(self, event):
        """Handle search input"""
        self.refresh()
    
    def on_filter_change(self, event):
        """Handle filter change"""
        self.refresh()
    
    def on_item_select(self, event):
        """Handle item selection"""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            order_id = item['values'][0]
            
            # Find the order by ID
            for order in self.orders:
                if order.id == order_id:
                    self.on_select_callback(order)
                    break

# Simple placeholder classes for other tabs (since the focus is on fixing the geometry error)
class IncomeExpenseTab:
    """Simple placeholder for Income & Expense tab"""
    def __init__(self, parent, database):
        self.parent = parent
        self.database = database
        ttk.Label(parent, text="Income & Expense Tab - Working!", font=('Arial', 16)).pack(pady=50)

class MonthlySummaryTab:
    """Simple placeholder for Monthly Summary tab"""
    def __init__(self, parent, database):
        self.parent = parent
        self.database = database
        ttk.Label(parent, text="Monthly Summary Tab - Working!", font=('Arial', 16)).pack(pady=50)

class AKCreativeApp:
    """Main application class - FIXED geometry management"""
    
    def __init__(self, root):
        self.root = root
        self.database = Database()
        
        self.setup_window()
        self.create_menu()
        self.create_widgets()
        self.refresh_orders()
    
    def setup_window(self):
        """Setup main window"""
        self.root.title(f"{APP_NAME} v{APP_VERSION} - {BUSINESS_NAME}")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom colors for AK Creative branding
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import Excel", command=self.import_excel)
        file_menu.add_command(label="Export All to Excel", command=self.export_all_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Backup Database", command=self.backup_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About AK Creative", command=self.show_about)
    
    def create_widgets(self):
        """Create main widgets - FIXED geometry management"""
        # Create header using PACK
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        title_label = ttk.Label(header_frame, text=f"{BUSINESS_NAME} - Order Tracking System v{APP_VERSION}", 
                               style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        # Current date/time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        time_label = ttk.Label(header_frame, text=f"📅 {current_time}")
        time_label.pack(side=tk.RIGHT)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Orders tab - FIXED
        self.orders_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.orders_frame, text="📋 Orders")
        self.create_orders_tab()
        
        # Income & Expense tab
        self.income_expense_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.income_expense_frame, text="💰 Income & Expense")
        self.income_expense_tab = IncomeExpenseTab(self.income_expense_frame, self.database)
        
        # Monthly Summary tab
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="📊 Monthly Summary")
        self.summary_tab = MonthlySummaryTab(self.summary_frame, self.database)
    
    def create_orders_tab(self):
        """Create orders tab with FIXED geometry management"""
        # Create paned window
        paned = ttk.PanedWindow(self.orders_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Order form
        left_frame = ttk.LabelFrame(paned, text="📝 Order Entry Form", padding="10")
        paned.add(left_frame, weight=1)
        self.order_form = OrderForm(left_frame, self.on_order_saved)
        
        # Right panel - Order list
        right_frame = ttk.LabelFrame(paned, text="📋 Orders Management", padding="10")
        paned.add(right_frame, weight=2)
        self.order_list = OrderList(right_frame, self.on_order_selected)
    
    def on_order_saved(self, order: Order, delete=False):
        """Handle order save/delete"""
        try:
            if delete:
                self.database.delete_order(order.id)
                messagebox.showinfo("Success", "✅ Order deleted successfully!")
                self.order_form.clear_form()
            elif order.id:
                self.database.update_order(order.id, order)
                message = "✅ Order updated successfully!"
                if order.payment_received == "Yes" and order.paid_amount > 0:
                    message += "\n💰 Sales transaction was automatically updated."
                messagebox.showinfo("Success", message)
            else:
                self.database.create_order(order)
                message = "✅ Order created successfully!"
                if order.payment_received == "Yes" and order.paid_amount > 0:
                    message += "\n💰 Sales transaction was automatically generated."
                messagebox.showinfo("Success", message)
                self.order_form.clear_form()
            
            self.refresh_orders()
            
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to save order: {str(e)}")
    
    def on_order_selected(self, order: Order):
        """Handle order selection"""
        self.order_form.load_order(order)
    
    def refresh_orders(self):
        """Refresh orders list"""
        try:
            orders = self.database.get_all_orders()
            self.order_list.refresh(orders)
        except Exception as e:
            messagebox.showerror("Error", f"❌ Failed to refresh orders: {str(e)}")
    
    def import_excel(self):
        """Import from Excel - placeholder"""
        messagebox.showinfo("Import Excel", "📤 Excel import feature coming soon!")
    
    def export_all_excel(self):
        """Export all data to Excel - placeholder"""
        messagebox.showinfo("Export Excel", "📥 Excel export feature coming soon!")
    
    def backup_database(self):
        """Create database backup - placeholder"""
        messagebox.showinfo("Backup Database", "💾 Database backup feature coming soon!")
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""{APP_NAME} v{APP_VERSION}

🏢 Professional Order Tracking System
Designed specifically for {BUSINESS_NAME}

Created by: {AUTHOR}
Date: {CREATED_DATE}
Location: Tanzania 🇹🇿

🔧 FIXED: Geometry manager conflicts
✅ All widgets now use consistent PACK layout
✅ No more grid/pack mixing errors

© 2025 AK Creative - All rights reserved"""
        
        messagebox.showinfo("About AK Creative Order Tracker", about_text)

def main():
    """Main entry point"""
    try:
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Create main window
        root = tk.Tk()
        app = AKCreativeApp(root)
        
        # Center window on screen
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Handle window closing
        def on_closing():
            if messagebox.askokcancel("Quit", f"Do you want to exit {APP_NAME}?"):
                logging.info("Application closed by user")
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start the application
        logging.info(f"Starting {APP_NAME} v{APP_VERSION} - Geometry Fixed")
        print(f"🚀 {APP_NAME} v{APP_VERSION} - Geometry Manager Fixed!")
        root.mainloop()
        
    except Exception as e:
        error_msg = f"Failed to start {APP_NAME}: {str(e)}"
        print(error_msg)
        try:
            messagebox.showerror("Application Error", error_msg)
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()