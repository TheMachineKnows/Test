from flask import Flask, g, request, render_template, jsonify, redirect
import sqlite3
import requests
from datetime import datetime

DATABASE = 'database.db'

# Initialize Flask application
app = Flask(__name__)

app.secret_key = "verysecret1981"

#barcode = 3017624010701

# Function to get the database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
         # Set row_factory to make rows behave like dicts
        db.row_factory = sqlite3.Row
    return db
# This function is used for connecting to openfoodfactsAPI
def get_food_fact(barcode):
    url = f"https://world.openfoodfacts.net/api/v2/product/{barcode}.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an exception for bad status codes
        data = response.json()
        if data.get('status')== 1: #If a product was found
            product = data['product']
            return {
                'name': product.get('product_name')
                }
        else:
            return {"error": "Product not found"}
    except requests.RequestException as e:
        return {"error": str(e)}

#Function to handle search form
@app.route('/search', methods=['POST']) 
def search_by_barcode():
    barcode = request.form.get('barcode')
    if not barcode:
        return "Please provide a barcode.", 400

    product_info = get_food_fact(barcode)
    if 'error' in product_info:
        return render_template('search_result.html', error=product_info['error'])
    else:
        return render_template('search_result.html', product=product_info)

# Function to clean up database connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Home route
@app.route('/')
def index():
    db = get_db()
    cursor = db.execute('SELECT * FROM entries')
    items = cursor.fetchall()
    return render_template("index.html", items=items)

# Route to add a new item to the inventory
@app.route('/add', methods=['POST'])
def add_item():
    db = get_db()
    # Extract data from the POST request
    name = request.form['name']
    quantity = request.form['quantity']
    expiration_date = request.form.get('expiration_date', None)
    
    # Validate expiration date if provided
    if expiration_date:
        try:
            datetime.strptime(expiration_date, '%Y-%m-%d')
        except ValueError:
            # Return error if date format is not correct
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Insert new item into the database
    db.execute('INSERT INTO entries (name, quantity, expiration_date) VALUES (?, ?, ?)',
               (name, quantity, expiration_date))
    db.commit()
    return redirect('/')

# Route to remove an item from the inventory
@app.route('/remove', methods=['POST'])
def remove_item():
    db = get_db()
    # Get the name of the item to remove
    name = request.form['name']
    
    # Check if the item exists in the database
    cursor = db.execute('SELECT id FROM entries WHERE name = ?', (name,))
    item = cursor.fetchone()
    
    if item:
        # If found, delete the item
        db.execute('DELETE FROM entries WHERE id = ?', (item['id'],))
        db.commit()
        return redirect('/')
    else:
        # If not found, return an error
        return jsonify({"error": "Item not found"}), 404
    
# Route to list all items in the inventory
@app.route('/entries', methods=['GET'])
def list_items():
    db = get_db()
    # Query all items from the database
    cursor = db.execute('SELECT * FROM entries')
    items = cursor.fetchall()
    return render_template('entries.html', entries = items)
    # Convert the result into a list of dictionaries
    #return jsonify([dict(row) for row in items]), 200

@app.route('/update-quantity', methods=['POST'])
def update_quantity():
    db=get_db()
    item_id=request.form['item_id']
    new_quantity = request.form['quantity']
    db.execute('UPDATE entries SET quantity = ? WHERE id = ?', (new_quantity, item_id))
    db.commit()
    return redirect('/entries')

@app.route('/delete-item', methods=['POST'])
def delete_item():
    db = get_db()
    item_id = request.form['item_id']
    db.execute('DELETE FROM entries WHERE id = ?', (item_id,))
    db.commit()
    return redirect('/entries')


if __name__ == '__main__':
    # Run the Flask app in debug mode. The host parameter makes the host
    # visible to all devices on the local network.
    app.run(debug=True, host='0.0.0.0')
