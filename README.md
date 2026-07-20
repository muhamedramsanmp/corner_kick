# ⚽ Corner Kick

A full-featured e-commerce web application built with Django that provides a complete online shopping experience with secure authentication, product management, online payments, wallet transactions, offers, coupons, and order management.

---

## 📌 Project Overview

Corner Kick is an online shopping platform developed using Django and PostgreSQL. The application allows users to browse products, manage their cart and wishlist, place orders using multiple payment methods, apply coupons and offers, submit product reviews, and track their orders.

The project also includes a powerful admin dashboard for managing products, categories, orders, offers, coupons, reports, and customer interactions.

---

## 🚀 Features

### 👤 User Features

* User Registration with Email Verification
* Secure Login and Logout
* Forgot Password Functionality
* User Profile Management
* Address Management
* Product Search and Filtering
* Product Variants (Size and Color)
* Shopping Cart Management
* Wishlist Management
* Coupon Application
* Product Offers and Discounts
* Razorpay Payment Integration
* Wallet Payment System
* Order Placement and Tracking
* Order Cancellation
* Product Return Requests
* Review and Rating System
* Download Invoice
* Referral Reward System

---

### 🛠️ Admin Features

* Admin Dashboard
* Product Management
* Category Management
* Variant Management
* Order Management
* Coupon Management
* Offer Management
* Review Moderation
* User Management
* Sales Reports
* Revenue Analytics
* Return Request Management

---

## 🏗️ Core Modules

* Authentication System
* Product Management System
* Cart System
* Wishlist System
* Checkout System
* Coupon System
* Offer Management System
* Wallet System
* Payment Gateway Integration
* Order Management System
* Return and Refund System
* Review and Rating System
* Reporting System

---

## 💳 Payment Methods

The application supports multiple payment options:

* Cash on Delivery (COD)
* Razorpay Online Payment
* Wallet Payment

---

## 🛒 Order Workflow

1. User registers and logs in.
2. User browses products.
3. Products are added to cart or wishlist.
4. User selects delivery address.
5. Coupon and offers are applied automatically.
6. User selects payment method.
7. Order is created successfully.
8. User can track, cancel, or return orders.
9. Refunds are credited to the wallet when applicable.

---

## 🧰 Technologies Used

### Backend

* Python
* Django
* PostgreSQL

### Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap 5

### Payment Gateway

* Razorpay

### Deployment & Hosting

* AWS EC2
* Gunicorn
* Nginx
* PostgreSQL
* SSL Certificate (Let's Encrypt)

### Version Control

* Git
* GitHub

---

## 📂 Project Structure

```text
corner_kick/
│
├── accounts/
├── products/
├── userinfo/
├── addressinfo/
├── user_orders/
├── admin_products/
├── admin_coupon/
├── admin_offer/
├── templates/
├── static/
├── media/
├── manage.py
└── requirements.txt
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
```

### 2. Move into the project directory

```bash
cd corner_kick
```

### 3. Create virtual environment

```bash
python -m venv venv
```

### 4. Activate virtual environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux/Mac

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

Create a `.env` file and add:

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_NAME=your_database_name
DATABASE_USER=your_database_user
DATABASE_PASSWORD=your_database_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password

RAZORPAY_KEY_ID=your_key
RAZORPAY_KEY_SECRET=your_secret
```

### 7. Apply migrations

```bash
python manage.py migrate
```

### 8. Create superuser

```bash
python manage.py createsuperuser
```

### 9. Collect static files

```bash
python manage.py collectstatic
```

### 10. Run the development server

```bash
python manage.py runserver
```

---

## 🌐 Deployment

The project is deployed using:

* AWS EC2 Ubuntu Server
* Gunicorn as WSGI Server
* Nginx as Reverse Proxy
* PostgreSQL Database
* SSL with Let's Encrypt
* Custom Domain Configuration

---

## 📊 Reports Available

* Sales Report
* Order Report
* Revenue Report
* Product Performance Report
* Coupon Usage Report

---

## 🔐 Security Features

* CSRF Protection
* Secure Password Hashing
* Authentication Middleware
* Session Management
* Form Validation
* Protected Routes using Login Required Decorators

---

## 📷 Screenshots

You can add screenshots of:

* Home Page
* Product Page
* Cart Page
* Checkout Page
* Order Page
* Admin Dashboard

---

## 👨‍💻 Author

**Muhamed Ramsan MP**

* Django Developer
* Python Developer
* Full Stack Developer Enthusiast

---

## 📄 License

This project is developed for educational and portfolio purposes.

---