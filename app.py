import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import json



app = Flask(__name__)
CORS(app)  # Enable frontend-backend communication

# Dynamically locate the database in the same directory as app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "store.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Models (Database Tables)
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, default=0)
    type = db.Column(db.String(10), nullable=False)  # 'enli' or 'ensiz'
    colour = db.Column(db.String(50), nullable=True)
    supplier = db.Column(db.String(100))
    total_quantity = db.Column(db.Float, default=0)  # Tracks total stock


class MaterialRoll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    material = db.relationship("Material", backref=db.backref("rolls", lazy=True))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    debt = db.Column(db.Float, default=0.0)
    location = db.Column(db.String(100))

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=True)
    quantity_sold = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


    material = db.relationship("Material", backref=db.backref("sales", lazy=True))
    customer = db.relationship("Customer", backref=db.backref("purchases", lazy=True))

class Processing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    sent_quantity = db.Column(db.Float, nullable=False)
    received_quantity = db.Column(db.Float)
    service_provider = db.Column(db.String(100))
    date_sent = db.Column(db.DateTime)
    date_received = db.Column(db.DateTime)


#  Activity Log Table (Tracks all actions)
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(20), nullable=False)  # SALE, DELETE, UPDATE
    table_name = db.Column(db.String(50), nullable=False)  # sales, materials, customers
    record_id = db.Column(db.Integer, nullable=False)  # ID of affected record
    changes = db.Column(db.Text, nullable=False)  # Store changes as JSON
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

#  Function to Log Activity
def log_activity(action_type, table_name, record_id, changes):
    new_log = ActivityLog(
        action_type=action_type,
        table_name=table_name,
        record_id=record_id,
        changes=json.dumps(changes, default=str)  # Convert changes to JSON
    )
    db.session.add(new_log)
    db.session.commit()


#  API to Add a New Material (One-time setup per material type)
@app.route("/api/materials", methods=["POST"])
def add_material():
    data = request.json
    existing_material = Material.query.filter_by(name=data["name"], type=data["type"],
                                                 supplier=data["supplier"]).first()

    if existing_material:
        return jsonify({"message": "Material already exists, use /api/add_rolls instead"}), 400

    new_material = Material(
        name=data["name"],
        type=data["type"],
        colour=data.get("colour"),
        supplier=data["supplier"]
    )

    db.session.add(new_material)
    db.session.commit()

    log_activity("ADD", "materials", new_material.id, data)

    return jsonify({"message": "Material added successfully!", "material_id": new_material.id}), 201


#  API to Add Multiple Rolls for an Existing Material
@app.route("/api/add_rolls", methods=["POST"])
def add_rolls():
    data = request.json
    material = Material.query.filter_by(name=data["name"], type=data["type"]).first()

    if not material:
        return jsonify({"error": "Material not found, please add it first using /api/materials"}), 404

    roll_quantities = data["quantities"]  # List of roll quantities
    roll_entries = [MaterialRoll(material_id=material.id, quantity=q) for q in roll_quantities]

    db.session.bulk_save_objects(roll_entries)
    db.session.commit()

    # Log Activity
    log_activity("ADD", "material_rolls", material.id, {"added_rolls": roll_quantities})

    return jsonify({"message": f"{len(roll_quantities)} rolls added successfully!", "material_id": material.id}), 201


#  API to Retrieve All Materials with Rolls
@app.route("/api/materials", methods=["GET"])
def get_materials():
    materials = Material.query.all()
    results = []
    for material in materials:
        material_data = {
            "id": material.id,
            "name": material.name,
            "type": material.type,
            "colour": material.colour,
            "supplier": material.supplier,
            "rolls": [{"id": roll.id, "quantity": roll.quantity, "date_added": roll.date_added} for roll in
                      material.rolls]
        }
        results.append(material_data)
    return jsonify(results)


#  API to Retrieve a Single Material and Its Rolls
@app.route("/api/material/<int:material_id>", methods=["GET"])
def get_single_material(material_id):
    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "Material not found"}), 404

    material_data = {
        "id": material.id,
        "name": material.name,
        "type": material.type,
        "colour": material.colour,
        "supplier": material.supplier,
        "rolls": [{"id": roll.id, "quantity": roll.quantity, "date_added": roll.date_added} for roll in material.rolls]
    }
    return jsonify(material_data)


#  API to Delete a Material and All Associated Rolls
@app.route("/api/material/<int:material_id>", methods=["DELETE"])
def delete_material(material_id):
    material = Material.query.get(material_id)
    if not material:
        return jsonify({"error": "Material not found"}), 404

    # Delete all rolls associated with this material
    MaterialRoll.query.filter_by(material_id=material.id).delete()

    db.session.delete(material)
    db.session.commit()

    log_activity("DELETE", "materials", material_id, {"deleted_material": material.name})

    return jsonify({"message": "Material and associated rolls deleted successfully"}), 200


#  API to Delete a Specific Roll Entry
@app.route("/api/roll/<int:roll_id>", methods=["DELETE"])
def delete_roll(roll_id):
    roll = MaterialRoll.query.get(roll_id)
    if not roll:
        return jsonify({"error": "Roll not found"}), 404

    deleted_data = {"material_id": roll.material_id, "quantity": roll.quantity}

    db.session.delete(roll)
    db.session.commit()

    log_activity("DELETE", "material_rolls", roll_id, {"deleted_roll": deleted_data})

    return jsonify({"message": "Roll deleted successfully"}), 200


#  API to Update a Roll Quantity
@app.route("/api/roll/<int:roll_id>", methods=["PUT"])
def update_roll(roll_id):
    data = request.json
    roll = MaterialRoll.query.get(roll_id)
    if not roll:
        return jsonify({"error": "Roll not found"}), 404

    old_quantity = roll.quantity  # Save old value before updating
    roll.quantity = data["quantity"]

    db.session.commit()

    log_activity("UPDATE", "material_rolls", roll_id,
                 {"before": {"quantity": old_quantity}, "after": {"quantity": roll.quantity}})

    return jsonify({"message": "Roll updated successfully!"}), 200


#  API to Get All Customers
@app.route("/api/customers", methods=["GET"])
def get_customers():
    customers = Customer.query.all()
    return jsonify([{"id": c.id, "name": c.name, "contact": c.contact, "debt": c.debt} for c in customers])


#  API to Add a New Customer
@app.route("/api/customers", methods=["POST"])
def add_customer():
    data = request.json
    new_customer = Customer(name=data["name"], contact=data["contact"], debt=0.0)
    db.session.add(new_customer)
    db.session.commit()

    log_activity("ADD", "customers", new_customer.id, {"name": data["name"], "contact": data["contact"]})

    return jsonify({"message": "Customer added successfully!", "customer_id": new_customer.id}), 201


#  API to Edit Customer Details
@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def edit_customer(customer_id):
    data = request.json
    customer = Customer.query.get(customer_id)

    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    old_data = {"name": customer.name, "contact": customer.contact, "debt": customer.debt}
    customer.name = data.get("name", customer.name)
    customer.contact = data.get("contact", customer.contact)
    db.session.commit()

    log_activity("UPDATE", "customers", customer.id, {"before": old_data, "after": data})

    return jsonify({"message": "Customer updated successfully!"})


#  API to Delete a Customer
@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    deleted_data = {"name": customer.name, "contact": customer.contact}
    db.session.delete(customer)
    db.session.commit()

    log_activity("DELETE", "customers", customer_id, {"deleted_customer": deleted_data})

    return jsonify({"message": "Customer deleted successfully!"})


#  API to Record a Sale & Update Stock
@app.route("/api/sales", methods=["POST"])
def add_sale():
    data = request.json
    material = Material.query.get(data["material_id"])
    customer = Customer.query.get(data["customer_id"])

    if not material:
        return jsonify({"error": "Material not found"}), 404

    if material.total_quantity < data["quantity_sold"]:
        return jsonify({"error": "Insufficient stock"}), 400

    # Deduct the quantity from total stock
    material.total_quantity -= data["quantity_sold"]

    # Add sale record
    new_sale = Sale(
        material_id=data["material_id"],
        customer_id=data["customer_id"],
        quantity_sold=data["quantity_sold"],
        price=data["price"],
        date=datetime.utcnow()
    )
    db.session.add(new_sale)

    # If customer has debt, update it
    if customer and "amount_due" in data:
        customer.debt += data["amount_due"]  # Add pending payment

    db.session.commit()

    # Log Activity
    log_activity("SALE", "sales", new_sale.id, {
        "material_id": data["material_id"],
        "customer_id": data["customer_id"],
        "quantity_sold": data["quantity_sold"],
        "price": data["price"]
    })

    return jsonify({"message": "Sale recorded successfully!"})


#  API to Get All Sales
@app.route("/api/sales", methods=["GET"])
def get_sales():
    sales = Sale.query.all()
    return jsonify([
        {
            "id": s.id,
            "material": s.material.name,
            "customer": s.customer.name if s.customer else "Walk-in Customer",
            "quantity_sold": s.quantity_sold,
            "price": s.price,
            "date": s.date
        }
        for s in sales
    ])


#  API to Edit a Sale
@app.route("/api/sales/<int:sale_id>", methods=["PUT"])
def edit_sale(sale_id):
    data = request.json
    sale = Sale.query.get(sale_id)

    if not sale:
        return jsonify({"error": "Sale not found"}), 404

    old_data = {"quantity_sold": sale.quantity_sold, "price": sale.price}

    old_quantity = sale.quantity_sold  # Store old quantity for stock adjustment
    sale.quantity_sold = data.get("quantity_sold", sale.quantity_sold)
    sale.price = data.get("price", sale.price)

    # Adjust stock levels
    sale.material.total_quantity += old_quantity  # Revert old quantity
    sale.material.total_quantity -= sale.quantity_sold  # Deduct new quantity

    db.session.commit()

    log_activity("UPDATE", "sales", sale.id, {"before": old_data, "after": data})

    return jsonify({"message": "Sale updated successfully!"})


#  API to Delete a Sale & Restore Stock
@app.route("/api/sales/<int:sale_id>", methods=["DELETE"])
def delete_sale(sale_id):
    sale = Sale.query.get(sale_id)
    if not sale:
        return jsonify({"error": "Sale not found"}), 404

    deleted_data = {
        "material_id": sale.material_id,
        "customer_id": sale.customer_id,
        "quantity_sold": sale.quantity_sold,
        "price": sale.price,
        "date": sale.date
    }

    sale.material.total_quantity += sale.quantity_sold
    db.session.delete(sale)
    db.session.commit()

    log_activity("DELETE", "sales", sale_id, {"deleted_sale": deleted_data})

    return jsonify({"message": "Sale deleted and stock restored!"})


@app.route("/api/logs", methods=["GET"])
def get_logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    return jsonify([
        {
            "id": log.id,
            "action_type": log.action_type,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "changes": json.loads(log.changes),
            "timestamp": log.timestamp
        }
        for log in logs
    ])

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
