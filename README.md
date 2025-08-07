# AK Creative Order Tracking System

A comprehensive web application for managing orders, income, and expenses for AK Creative - a Tanzanian creative services business.

## Features

### 🛒 Order Management
- Track customer orders for creative products (Picha, Banner, Holder, Notebook, Poster, Sticker, Design)
- Manage order details including quantities, pricing, and payment status
- Automatic currency conversion between TZS (primary) and USD

### 💰 Income & Expenses Tracking
- **Auto-Generated Sales**: Sales transactions automatically created when orders are marked as paid
- **Manual Expense Entry**: Add business expenses with predefined categories
- **Dual Currency Support**: Primary amounts in TZS with automatic USD conversion
- **Visual Separation**: Clear distinction between sales and expenses with color coding

### 📊 Business Intelligence
- Real-time financial summaries (Total Sales, Total Expenses, Net Income)
- Transaction filtering (Sales Only, Expenses Only, All)
- Status indicators for auto-generated vs manual entries
- Monthly/periodic reporting capabilities

## Product Categories

### Creative Products (Sales Items)
- **Picha** - Photo prints and portraits
- **Banner** - Advertising banners
- **Holder** - Document holders
- **Notebook** - Custom notebooks
- **Poster** - Promotional posters
- **Sticker** - Custom stickers
- **Design** - Custom design services

### Business Expense Categories
- **Business Operations**: Transport, Meals, Office Supplies
- **Fixed Costs**: Rent, Salaries, Electricity, Water, Internet, Security, Trash

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## Database Schema

### Orders Table
- Customer information and order details
- Item types from predefined creative product catalog
- Payment status tracking
- Currency amounts in both TZS and USD

### Transactions Table
- Income and expense tracking
- Auto-generated sales linked to orders
- Manual expense entries
- Category distinction (Sales/Expenses)
- Auto-generation flags for audit trail

## Business Logic

### Auto-Generated Sales
1. When an order's payment status is changed to "Yes"
2. A sales transaction is automatically created
3. Transaction is linked to the original order
4. Sales entries are read-only to maintain data integrity

### Manual Expense Entry
1. Select from predefined expense categories
2. Enter amount in TZS (primary currency)
3. USD amount automatically calculated
4. Full edit capabilities for manual entries

### Currency Conversion
- Exchange rate: 1 USD = 2,500 TZS (approximate)
- All primary amounts entered in TZS
- USD amounts auto-calculated for reference
- Rate can be updated in the application code

## Technical Stack

- **Backend**: Python Flask
- **Database**: SQLite (for simplicity and portability)
- **Frontend**: Bootstrap 5 with custom CSS
- **Icons**: Font Awesome
- **Responsive Design**: Mobile-friendly interface

## Business Context

This system is specifically designed for AK Creative, a Tanzanian creative services business, with:
- TZS as the primary currency
- USD as secondary reference currency
- Specific product catalog for creative services
- Business expense categories relevant to creative services in Tanzania

## Usage Workflow

1. **Add Orders**: Create customer orders with product details
2. **Track Payments**: Update payment status to auto-generate sales
3. **Manage Expenses**: Add business expenses manually
4. **Monitor Finances**: View income & expenses dashboard with real-time summaries
5. **Generate Reports**: Filter and analyze financial data

The system streamlines business operations by automatically linking paid orders to sales revenue while providing comprehensive expense tracking capabilities.