from datetime import datetime
from io import StringIO, BytesIO
from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
import csv
from sqlalchemy import func

app = Flask(__name__)

# Configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
db = SQLAlchemy(app)


# Expense Model for SQLAlchemy
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


# Linked List Implementation
class ExpenseNode:
    def __init__(self, id, amount, description, category, type, date):
        self.id = id
        self.amount = amount
        self.description = description
        self.category = category
        self.type = type
        self.date = date
        self.next = None


class ExpenseLinkedList:
    def __init__(self):
        self.head = None

    def add_expense(self, id, amount, description, category, type, date):
        new_node = ExpenseNode(id, amount, description, category, type, date)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node

    def get_all_expenses(self):
        expenses = []
        current = self.head
        while current:
            expenses.append({
                "id": current.id,
                "amount": current.amount,
                "description": current.description,
                "category": current.category,
                "type": current.type,
                "date": current.date.isoformat()
            })
            current = current.next
        return expenses

    def delete_expense(self, id):
        if not self.head:
            return False

        if self.head.id == id:
            self.head = self.head.next
            return True

        current = self.head
        while current.next:
            if current.next.id == id:
                current.next = current.next.next
                return True
            current = current.next

        return False

    def get_summary(self):
        total_expense = 0
        total_income = 0
        current = self.head
        while current:
            if current.type == 'expense':
                total_expense += current.amount
            elif current.type == 'income':
                total_income += current.amount
            current = current.next

        net_balance = total_income - total_expense
        return {
            "totalExpense": round(total_expense, 2),
            "totalIncome": round(total_income, 2),
            "netBalance": round(net_balance, 2)
        }


# Initialize the linked list
expense_list = ExpenseLinkedList()


# Helper function to choose between SQLAlchemy and Linked List
def use_linked_list():
    return request.args.get('use_linked_list', '').lower() == 'true'


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

        if use_linked_list():
            new_id = len(expense_list.get_all_expenses()) + 1
            expense_list.add_expense(
                id=new_id,
                amount=amount,
                description=data['description'],
                category=data['category'],
                type=data['type'],
                date=date
            )
            return jsonify({"message": "Entry added successfully", "id": new_id}), 201
        else:
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
        if not use_linked_list():
            db.session.rollback()
        app.logger.error(f"Error adding expense: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route('/expenses', methods=['GET'])
def get_expenses():
    if use_linked_list():
        expenses = expense_list.get_all_expenses()
        return jsonify(expenses)
    else:
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
        if use_linked_list():
            if expense_list.delete_expense(entry_id):
                return jsonify({"message": "Entry deleted successfully"}), 200
            else:
                return jsonify({"error": "Entry not found"}), 404
        else:
            entry = Expense.query.get(entry_id)
            if entry:
                db.session.delete(entry)
                db.session.commit()
                return jsonify({"message": "Entry deleted successfully"}), 200
            else:
                return jsonify({"error": "Entry not found"}), 404
    except Exception as e:
        if not use_linked_list():
            db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/export', methods=['GET'])
def export_csv():
    try:
        if use_linked_list():
            expenses = expense_list.get_all_expenses()
        else:
            expenses = Expense.query.all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Amount', 'Description', 'Category', 'Type', 'Date'])

        for exp in expenses:
            if use_linked_list():
                writer.writerow(
                    [exp['id'], exp['amount'], exp['description'], exp['category'], exp['type'], exp['date']])
            else:
                writer.writerow([exp.id, exp.amount, exp.description, exp.category, exp.type, exp.date.isoformat()])

        output.seek(0)
        return send_file(
            BytesIO(output.getvalue().encode()),
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
        if use_linked_list():
            return jsonify(expense_list.get_summary())
        else:
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