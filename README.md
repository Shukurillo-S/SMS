# SMS - Store Management System

This is a **desktop application** built using **Electron.js, React, Flask, and SQLite** for managing materials, tracking sales, handling customers, and maintaining logs.

**Key Features:**
- Add, update, and delete **materials** and **customer details**.
- Track **inventory** with roll-based materials.
- Log **sales transactions** and update stock levels automatically.
- Maintain **processing records** for materials sent for external processing.
- Store **activity logs** to track database changes.

### 🛠 Technologies Used:
- **Frontend:** Electron.js, React.js, Axios
- **Backend:** Flask, SQLite, Flask-SQLAlchemy
- **API Communication:** REST API using Flask

###   API Routes:
####  Materials
- `POST /api/materials` → Add new material
- `GET /api/materials` → Fetch all materials
- `DELETE /api/material/<id>` → Delete a material

####  Sales
- `POST /api/sales` → Record a sale
- `GET /api/sales` → Fetch all sales
- `DELETE /api/sales/<id>` → Delete a sale

####  Customers
- `POST /api/customers` → Add new customer
- `GET /api/customers` → Fetch all customers
- `PUT /api/customers/<id>` → Update customer
