from flask import Flask, render_template, redirect, url_for, session, flash, request, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField,DecimalField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
import bcrypt
from flask_mysqldb import MySQL
import os

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12Kazungu.'
app.config['MYSQL_DB'] = 'chemist'
app.secret_key = 'your_secret_key_here'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField("Register")

    def validate_email(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class EditForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Save Changes")

class AddToCartForm(FlaskForm):
    quantity = IntegerField("Quantity", validators=[DataRequired()])
    submit = SubmitField("Add to Cart")

class AddProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    price = DecimalField('Price', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    submit = SubmitField('Add Product')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, email, password FROM admin WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            flash("Login successful.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO admin (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
            mysql.connection.commit()
            cursor.close()
        except Exception as e:
            flash("An error occurred during registration. Please try again.", "danger")
            app.logger.error("Failed to register user: %s", e)
            return redirect(url_for('register'))

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/products')
def products():
    return render_template('products.html', products=products)

# Dummy data for products
products = {
    1: {"name": "Product 1", "price": 900, "image_url": "/static/images/product1.png"},
    2: {"name": "Product 2", "price": 300, "image_url": "/static/images/product2.png"},
    3: {"name": "Product 3", "price": 300, "image_url": "/static/images/product3.png"}
}


# Dummy data for the cart
cart = {}

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form['quantity'])
    if product_id in products:
        if product_id in cart:
            cart[product_id] += quantity
        else:
            cart[product_id] = quantity
    return redirect(url_for('view_cart'))
@app.route('/cart')
def view_cart():
    cart_items = {
        product_id: {
            "quantity": quantity,
            "name": products[product_id]["name"],
            "price": products[product_id]["price"],
            "image_url": products[product_id]["image_url"]
        }
        for product_id, quantity in cart.items()
    }
    total_price = sum(item['price'] * item['quantity'] for item in cart_items.values())
    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])

    if product_id in cart:
        cart[product_id] = quantity

    return redirect(url_for('view_cart'))

@app.route('/delete_item/<int:product_id>', methods=['POST'])
def delete_item(product_id):
    # Check if the product is in the cart
    if product_id in cart:
        # Remove the item from the cart
        del cart[product_id]
    return redirect(url_for('view_cart'))

# Define a route to render the form
@app.route('/add_product', methods=['GET'])
def add_product_form():
    return render_template('add_product.html')

# Define a route to handle form submission
@app.route('/add_product', methods=['POST'])
def add_product():
    # Get form data
    name = request.form['name']
    price = float(request.form['price'])
    description = request.form['description']
    image = request.files['image']

    # Save image to a folder
    image_path = os.path.join('uploads', image.filename)
    image.save(image_path)

    # Insert product data into the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO products (name, price, description, image) VALUES (%s, %s, %s, %s)",
                (name, price, description, image_path))
    mysql.connection.commit()
    cur.close()

    return 'Product added successfully'

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']

        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT name, email FROM admin WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            cursor.close()

            if user:
                user_name = user[0]
                user_email = user[1]
                return render_template('dashboard.html', user_name=user_name, user_email=user_email)
            else:
                flash("User not found", "danger")
                return redirect(url_for('login'))

        except Exception as e:
            flash("An error occurred while fetching user data", "danger")
            app.logger.error(f"Error fetching user data: {e}")
            return redirect(url_for('login'))

    return redirect(url_for('login'))

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    form = EditForm()
    if request.method == 'GET':
        # Retrieve user data from the database and pre-fill the form fields
        user_id = session.get('user_id')
        if user_id:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT name, email FROM admin WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            cursor.close()

            if user_data:
                form.name.data = user_data[0]
                form.email.data = user_data[1]
            else:
                flash("User data not found", "danger")
                return redirect(url_for('login'))
        else:
            flash("User not logged in", "danger")
            return redirect(url_for('login'))
    elif request.method == 'POST' and form.validate_on_submit():
        # Update user data in the database
        name = form.name.data
        email = form.email.data
        user_id = session.get('user_id')

        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE admin SET name = %s, email = %s WHERE id = %s", (name, email, user_id))
        mysql.connection.commit()
        cursor.close()

        flash("Profile updated successfully", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit.html', form=form)
# Mock sales data
sales_data = {
    "2024-05-17": [
        {"date": "2024-05-17", "product_name": "Medicine A", "quantity": 10, "total_price": 5000},
        {"date": "2024-05-17", "product_name": "Medicine B", "quantity": 5, "total_price": 2500}
    ],
    "2024-05-18": [
        {"date": "2024-05-18", "product_name": "Medicine C", "quantity": 8, "total_price": 4000},
    ]
}

@app.route('/fetch_sales_data', methods=['GET'])
def fetch_sales_data():
    date = request.args.get('date')
    sales = sales_data.get(date, [])
    return jsonify({"sales": sales})

if __name__ == '__main__':
    app.run(debug=True)
