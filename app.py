from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
import csv
from io import StringIO
from sqlalchemy import func

app = Flask(__name__)

# Configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db = SQLAlchemy(app)

# Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'expense' or 'income'
    date = db.Column(db.Date, nullable=False)

# Ensure the database tables are created
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/add', methods=['POST'])
def add_expense():
    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form

        # Validate required fields
        required_fields = ['amount', 'description', 'category', 'type', 'date']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate data types
        try:
            amount = float(data['amount'])
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError as e:
            return jsonify({"error": f"Invalid data format: {str(e)}"}), 400

        new_entry = Expense(
            amount=amount,
            description=data['description'],
            category=data['category'],
            type=data['type'],
            date=date
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"message": "Entry added successfully", "id": new_entry.id}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding expense: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
@app.route('/expenses', methods=['GET'])
def get_expenses():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    category = request.args.get('category')

    query = Expense.query

    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if category:
        query = query.filter(Expense.category == category)

    expenses = query.order_by(Expense.date.desc()).paginate(page=page, per_page=limit, error_out=False)

    return jsonify([{
        "id": exp.id,
        "amount": exp.amount,
        "description": exp.description,
        "category": exp.category,
        "type": exp.type,
        "date": exp.date.isoformat()
    } for exp in expenses.items])

@app.route('/delete/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    try:
        entry = Expense.query.get(entry_id)
        if entry:
            db.session.delete(entry)
            db.session.commit()
            return jsonify({"message": "Entry deleted successfully"}), 200
        else:
            return jsonify({"error": "Entry not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/export', methods=['GET'])
def export_csv():
    try:
        expenses = Expense.query.all()
        output = BytesIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Amount', 'Description', 'Category', 'Type', 'Date'])

        for exp in expenses:
            writer.writerow([exp.id, exp.amount, exp.description, exp.category, exp.type, exp.date.isoformat()])

        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='expenses.csv'
        )
    except Exception as e:
        app.logger.error(f"Error exporting CSV: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while exporting the CSV. Please try again."}), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    try:
        total_expense = db.session.query(func.sum(Expense.amount)).filter(Expense.type == 'expense').scalar() or 0
        total_income = db.session.query(func.sum(Expense.amount)).filter(Expense.type == 'income').scalar() or 0
        net_balance = total_income - total_expense

        return jsonify({
            "totalExpense": round(total_expense, 2),
            "totalIncome": round(total_income, 2),
            "netBalance": round(net_balance, 2)
        })
    except Exception as e:
        app.logger.error(f"Error fetching summary: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occurred while fetching the summary. Please try again."}), 500

if __name__ == '__main__':
    app.run(debug=True)