from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import json
import os
from anthropic import Anthropic
from collections import defaultdict
import calendar

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finwise.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'finwise-secret-key-2024'
db = SQLAlchemy(app)
import os
print("API KEY LOADED:", os.environ.get("ANTHROPIC_API_KEY","NOT FOUND"))

# ─── MODELS ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    age_group = db.Column(db.String(50))
    monthly_income = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), default='💰')
    color = db.Column(db.String(20), default='#10b981')
    type = db.Column(db.String(20), default='expense')  # income or expense

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # income or expense
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='transactions')
    date = db.Column(db.Date, nullable=False, default=date.today)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='budgets')
    limit_amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_age_group(age):
    if age < 18:
        return "Teen (Under 18)"
    elif age <= 25:
        return "Young Adult (18–25)"
    elif age <= 35:
        return "Adult (26–35)"
    elif age <= 50:
        return "Mid-Career (36–50)"
    elif age <= 65:
        return "Pre-Retirement (51–65)"
    else:
        return "Senior (65+)"

def get_current_user():
    return User.query.first()

def get_monthly_stats(month=None, year=None):
    if not month:
        month = date.today().month
    if not year:
        year = date.today().year
    
    transactions = Transaction.query.filter(
        db.extract('month', Transaction.date) == month,
        db.extract('year', Transaction.date) == year
    ).all()

    income = sum(t.amount for t in transactions if t.type == 'income')
    expenses = sum(t.amount for t in transactions if t.type == 'expense')
    
    category_spending = defaultdict(float)
    for t in transactions:
        if t.type == 'expense' and t.category:
            category_spending[t.category.name] += t.amount

    return {
        'income': income,
        'expenses': expenses,
        'balance': income - expenses,
        'transactions': transactions,
        'category_spending': dict(category_spending),
        'month': month,
        'year': year
    }

def seed_defaults():
    if Category.query.count() == 0:
        defaults = [
            Category(name='Salary', icon='briefcase', color='#d9a05b', type='income'),
            Category(name='Freelance', icon='laptop', color='#0ea5e9', type='income'),
            Category(name='Investment', icon='trending-up', color='#10b981', type='income'),
            Category(name='Food & Dining', icon='utensils', color='#eab308', type='expense'),
            Category(name='Transport', icon='car', color='#a1a1aa', type='expense'),
            Category(name='Shopping', icon='shopping-bag', color='#ec4899', type='expense'),
            Category(name='Entertainment', icon='clapperboard', color='#8b5cf6', type='expense'),
            Category(name='Health', icon='heart', color='#f43f5e', type='expense'),
            Category(name='Education', icon='book-open', color='#3b82f6', type='expense'),
            Category(name='Utilities', icon='zap', color='#eab308', type='expense'),
            Category(name='Rent', icon='home', color='#cca470', type='expense'),
            Category(name='Other', icon='package', color='#6b7280', type='expense'),
        ]
        db.session.add_all(defaults)
        db.session.commit()

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    return redirect(url_for('dashboard'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        data = request.json
        age = int(data['age'])
        user = User(
            name=data['name'],
            age=age,
            age_group=get_age_group(age),
            monthly_income=float(data.get('monthly_income', 0))
        )
        db.session.add(user)
        db.session.commit()
        seed_mock_transactions_and_budgets(user)
        return jsonify({'success': True})
    return render_template('setup.html')

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    if Transaction.query.count() == 0:
        seed_mock_transactions_and_budgets(user)
    stats = get_monthly_stats()
    return render_template('dashboard.html', user=user, stats=stats)

@app.route('/transactions')
def transactions():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    all_transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    categories = Category.query.all()
    return render_template('transactions.html', user=user, transactions=all_transactions, categories=categories)

@app.route('/budgets')
def budgets():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    month = date.today().month
    year = date.today().year
    all_budgets = Budget.query.filter_by(month=month, year=year).all()
    categories = Category.query.filter_by(type='expense').all()
    stats = get_monthly_stats()
    return render_template('budgets.html', user=user, budgets=all_budgets, categories=categories, stats=stats, month=month, year=year)

@app.route('/reports')
def reports():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    return render_template('reports.html', user=user)

@app.route('/categories')
def categories():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    all_categories = Category.query.all()
    return render_template('categories.html', user=user, categories=all_categories)

@app.route('/insights')
def insights():
    user = get_current_user()
    if not user:
        return redirect(url_for('setup'))
    return render_template('insights.html', user=user)

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.route('/api/dashboard-data')
def api_dashboard_data():
    stats = get_monthly_stats()
    
    # Last 6 months trend
    trends = []
    today = date.today()
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        s = get_monthly_stats(m, y)
        trends.append({
            'month': calendar.month_abbr[m],
            'income': s['income'],
            'expenses': s['expenses']
        })

    recent = Transaction.query.order_by(Transaction.date.desc()).limit(5).all()
    
    return jsonify({
        'income': stats['income'],
        'expenses': stats['expenses'],
        'balance': stats['balance'],
        'category_spending': stats['category_spending'],
        'trends': trends,
        'recent_transactions': [{
            'id': t.id,
            'title': t.title,
            'amount': t.amount,
            'type': t.type,
            'category': t.category.name if t.category else 'Other',
            'category_icon': t.category.icon if t.category else '📦',
            'category_color': t.category.color if t.category else '#94a3b8',
            'date': t.date.strftime('%b %d, %Y')
        } for t in recent]
    })

@app.route('/api/transactions', methods=['GET', 'POST'])
def api_transactions():
    if request.method == 'POST':
        data = request.json
        t = Transaction(
            title=data['title'],
            amount=float(data['amount']),
            type=data['type'],
            category_id=int(data['category_id']) if data.get('category_id') else None,
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            note=data.get('note', '')
        )
        db.session.add(t)
        db.session.commit()
        return jsonify({'success': True, 'id': t.id})
    
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'amount': t.amount,
        'type': t.type,
        'category': t.category.name if t.category else 'Other',
        'category_icon': t.category.icon if t.category else '📦',
        'category_color': t.category.color if t.category else '#94a3b8',
        'date': t.date.strftime('%Y-%m-%d'),
        'note': t.note or ''
    } for t in transactions])

@app.route('/api/transactions/<int:tid>', methods=['PUT', 'DELETE'])
def api_transaction(tid):
    t = Transaction.query.get_or_404(tid)
    if request.method == 'DELETE':
        db.session.delete(t)
        db.session.commit()
        return jsonify({'success': True})
    data = request.json
    t.title = data['title']
    t.amount = float(data['amount'])
    t.type = data['type']
    t.category_id = int(data['category_id']) if data.get('category_id') else None
    t.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    t.note = data.get('note', '')
    db.session.commit()
    return jsonify({'success': True})
@app.route('/api/budgets', methods=['GET', 'POST'])
def api_budgets():
    if request.method == 'POST':
        data = request.json
        month = date.today().month
        year = date.today().year
        existing = Budget.query.filter_by(category_id=data['category_id'], month=month, year=year).first()
        if existing:
            existing.limit_amount = float(data['limit_amount'])
        else:
            b = Budget(category_id=int(data['category_id']), limit_amount=float(data['limit_amount']), month=month, year=year)
            db.session.add(b)
        db.session.commit()
        return jsonify({'success': True})
    
    # GET handler
    month = date.today().month
    year = date.today().year
    budgets = Budget.query.filter_by(month=month, year=year).all()
    return jsonify([{
        'id': b.id,
        'category_id': b.category_id,
        'category': {
            'id': b.category.id,
            'name': b.category.name,
            'icon': b.category.icon,
            'color': b.category.color
        } if b.category else None,
        'limit_amount': b.limit_amount,
        'month': b.month,
        'year': b.year
    } for b in budgets])
@app.route('/api/budgets/<int:bid>', methods=['DELETE'])
def api_budget(bid):
    b = Budget.query.get_or_404(bid)
    db.session.delete(b)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/categories', methods=['GET', 'POST'])
def api_categories():
    if request.method == 'POST':
        data = request.json
        c = Category(name=data['name'], icon=data.get('icon', '📦'), color=data.get('color', '#94a3b8'), type=data.get('type', 'expense'))
        db.session.add(c)
        db.session.commit()
        return jsonify({'success': True, 'id': c.id})
    cats = Category.query.all()
    return jsonify([{'id': c.id, 'name': c.name, 'icon': c.icon, 'color': c.color, 'type': c.type} for c in cats])

@app.route('/api/categories/<int:cid>', methods=['DELETE'])
def api_category(cid):
    c = Category.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/reports-data')
def api_reports_data():
    months_data = []
    today = date.today()
    for i in range(11, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        s = get_monthly_stats(m, y)
        months_data.append({
            'month': f"{calendar.month_abbr[m]} {y}",
            'income': s['income'],
            'expenses': s['expenses'],
            'balance': s['balance'],
            'categories': s['category_spending']
        })
    return jsonify(months_data)

def seed_mock_transactions_and_budgets(user):
    import random
    from datetime import date
    
    # Get all categories
    categories = {c.name: c for c in Category.query.all()}
    
    today = date.today()
    month = today.month
    year = today.year
    
    # Clear existing data to clean-seed matching active age profile
    Transaction.query.delete()
    Budget.query.delete()
    db.session.commit()
    
    is_student = (user.age <= 21)
    
    if is_student:
        db.session.add(Budget(category_id=categories['Food & Dining'].id, limit_amount=4000.0, month=month, year=year))
        db.session.add(Budget(category_id=categories['Shopping'].id, limit_amount=2500.0, month=month, year=year))
        db.session.add(Budget(category_id=categories['Entertainment'].id, limit_amount=2000.0, month=month, year=year))
        
        income_val = user.monthly_income if user.monthly_income > 0 else 12000.0
    else:
        db.session.add(Budget(category_id=categories['Food & Dining'].id, limit_amount=12000.0, month=month, year=year))
        db.session.add(Budget(category_id=categories['Shopping'].id, limit_amount=6000.0, month=month, year=year))
        db.session.add(Budget(category_id=categories['Entertainment'].id, limit_amount=5000.0, month=month, year=year))
        
        income_val = user.monthly_income if user.monthly_income > 0 else 60000.0
    
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
            
        if is_student:
            # Student Income
            db.session.add(Transaction(
                title="Monthly Pocket Money",
                amount=income_val * 0.7,
                type='income',
                category_id=categories['Salary'].id,
                date=date(y, m, 1),
                note="Allowance from parents"
            ))
            if random.random() > 0.4:
                db.session.add(Transaction(
                    title="Part-time Tutoring",
                    amount=income_val * 0.3,
                    type='income',
                    category_id=categories['Freelance'].id,
                    date=date(y, m, 15),
                    note="Taught high school math"
                ))
                
            # Student Expenses
            db.session.add(Transaction(
                title="Jio Mobile Data Pack",
                amount=719.0,
                type='expense',
                category_id=categories['Utilities'].id,
                date=date(y, m, 5),
                note="Monthly phone internet recharge"
            ))
            
            # Education
            db.session.add(Transaction(
                title="College Notebooks & Stationery",
                amount=float(random.randint(150, 400)),
                type='expense',
                category_id=categories['Education'].id,
                date=date(y, m, 10)
            ))
            if random.random() > 0.5:
                db.session.add(Transaction(
                    title="Udemy Online Coding Course",
                    amount=499.0,
                    type='expense',
                    category_id=categories['Education'].id,
                    date=date(y, m, 18)
                ))
                
            # Food (small frequent food transactions)
            student_food = [
                ("College Canteen Lunch", 80, 150),
                ("Maggie & Chai Tapri", 45, 90),
                ("McDonalds Burger Meal", 220, 380),
                ("Domino's Pizza Hangout", 280, 500),
                ("Cafe Coffee Day Shake", 150, 260)
            ]
            for k in range(random.randint(4, 8)):
                title, min_a, max_a = random.choice(student_food)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Food & Dining'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Transport
            student_transport = [
                ("Metro Smartcard Topup", 200, 500),
                ("Local Shared Rickshaw", 40, 100),
                ("Scooter Petrol Refill", 400, 800)
            ]
            for k in range(random.randint(2, 3)):
                title, min_a, max_a = random.choice(student_transport)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Transport'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Shopping
            student_shopping = [
                ("H&M Thrift T-shirt", 450, 850),
                ("Amazon Gadget Cover", 250, 600),
                ("Local Thrift Sneakers", 999, 1800)
            ]
            for k in range(random.randint(1, 2)):
                title, min_a, max_a = random.choice(student_shopping)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Shopping'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Entertainment
            student_ent = [
                ("Spotify Student Plan", 59, 59),
                ("Netflix Mobile Premium", 149, 149),
                ("Movie Tickets & Popcorn", 250, 550),
                ("Steam Indie Game", 180, 450)
            ]
            for k in range(random.randint(1, 3)):
                title, min_a, max_a = random.choice(student_ent)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Entertainment'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
        else:
            # Regular Adult Income
            salary_date = date(y, m, 1)
            db.session.add(Transaction(
                title="Monthly Salary",
                amount=income_val,
                type='income',
                category_id=categories['Salary'].id,
                date=salary_date,
                note="Direct deposit from employer"
            ))
            if random.random() > 0.3:
                db.session.add(Transaction(
                    title="Freelance Design Gig",
                    amount=float(random.randint(60, 180) * 100),
                    type='income',
                    category_id=categories['Freelance'].id,
                    date=date(y, m, 12),
                    note="UI Design consulting"
                ))
                
            # Rent
            db.session.add(Transaction(
                title="Apartment Rent",
                amount=float(random.randint(140, 160) * 100),
                type='expense',
                category_id=categories['Rent'].id,
                date=date(y, m, 3),
                note="Monthly apartment rent transfer"
            ))
            
            # Utilities
            db.session.add(Transaction(
                title="Electricity Bill",
                amount=float(random.randint(18, 35) * 100),
                type='expense',
                category_id=categories['Utilities'].id,
                date=date(y, m, 5),
                note="State power board payment"
            ))
            
            db.session.add(Transaction(
                title="Broadband Internet",
                amount=999.0,
                type='expense',
                category_id=categories['Utilities'].id,
                date=date(y, m, 8),
                note="High-speed fiber connection"
            ))
            
            # Food
            food_titles = [
                ("Zomato Delivery", 350, 950),
                ("Swiggy Order", 250, 750),
                ("Grocery Shopping", 1200, 3500),
                ("Fine Dining", 1500, 4500),
                ("Starbucks Coffee", 180, 450),
                ("Weekend Brunch", 600, 1200)
            ]
            for k in range(random.randint(4, 7)):
                title, min_a, max_a = random.choice(food_titles)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Food & Dining'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Transport
            transport_titles = [
                ("Uber Ride", 150, 450),
                ("Ola Cab", 200, 600),
                ("Petrol Refill", 1000, 2500),
                ("Metro Recharge", 500, 1000)
            ]
            for k in range(random.randint(2, 4)):
                title, min_a, max_a = random.choice(transport_titles)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Transport'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Shopping
            shopping_titles = [
                ("Amazon Order", 800, 4500),
                ("Myntra App", 1200, 3000),
                ("Zara Apparel", 2500, 7000),
                ("Supermarket Run", 1000, 2500)
            ]
            for k in range(random.randint(1, 3)):
                title, min_a, max_a = random.choice(shopping_titles)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Shopping'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
            # Entertainment
            ent_titles = [
                ("Netflix Standard", 499, 499),
                ("Spotify Premium", 119, 119),
                ("Movie Tickets", 400, 900),
                ("Gaming Purchase", 1000, 3000),
                ("Concert Pass", 2500, 5000)
            ]
            for k in range(random.randint(1, 3)):
                title, min_a, max_a = random.choice(ent_titles)
                db.session.add(Transaction(
                    title=title,
                    amount=float(random.randint(min_a, max_a)),
                    type='expense',
                    category_id=categories['Entertainment'].id,
                    date=date(y, m, random.randint(2, 28))
                ))
                
    db.session.commit()

def get_mock_insights(insight_type, user, stats):
    import random
    from datetime import date
    
    # Calculate real numbers from stats
    income = float(stats['income'])
    expenses = float(stats['expenses'])
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else 0
    
    # Get active budgets to extract real limits
    budgets = Budget.query.filter_by(month=date.today().month, year=date.today().year).all()
    budget_details = []
    for b in budgets:
        spent = stats['category_spending'].get(b.category.name, 0)
        budget_details.append({
            'name': b.category.name,
            'limit': b.limit_amount,
            'spent': spent,
            'pct': (spent / b.limit_amount * 100) if b.limit_amount > 0 else 0
        })

    if insight_type == 'savings':
        dining_spent = stats['category_spending'].get('Food & Dining', 3200.0)
        shopping_spent = stats['category_spending'].get('Shopping', 2400.0)
        
        tips = [
            {
                "title": "Audit Food & Dining leaks",
                "description": f"You spent ₹{dining_spent:,.0f} on Food & Dining this month. Reducing deliveries by 25% will redirect approximately ₹{(dining_spent * 0.25):,.0f} to your savings.",
                "potential_saving": int(dining_spent * 0.25),
                "type": "warning" if dining_spent > 5000 else "tip"
            },
            {
                "title": "Optimize shopping velocity",
                "description": f"Your Shopping category total stands at ₹{shopping_spent:,.0f}. Introducing a 48-hour cool-off period before buying non-essentials can save you ₹{(shopping_spent * 0.3):,.0f} next month.",
                "potential_saving": int(shopping_spent * 0.3),
                "type": "tip"
            }
        ]
        
        if savings_rate > 20:
            tips.append({
                "title": "Leverage compound interest",
                "description": f"With a healthy saving of ₹{savings:,.0f} ({savings_rate:.0f}% rate), consider moving ₹{(savings * 0.5):,.0f} into low-cost index funds to accelerate wealth building.",
                "potential_saving": int(savings * 0.5),
                "type": "tip"
            })
        else:
            tips.append({
                "title": "Boost low savings velocity",
                "description": f"You saved only ₹{savings:,.0f} this month. Trimming subscriptions and utilities by 15% can add ₹1,500 to your savings pool.",
                "potential_saving": 1500,
                "type": "warning"
            })
        return tips

    elif insight_type == 'forecast':
        predicted_income = income if income > 0 else (float(user.monthly_income) if user.monthly_income > 0 else 50000.0)
        variance = random.uniform(0.95, 1.05)
        predicted_expenses = (expenses if expenses > 0 else 30000.0) * variance
        
        predicted_savings = predicted_income - predicted_expenses
        outlook = "positive" if predicted_savings >= 0 else "concerning"
        
        risk_areas = [b['name'] for b in budget_details if b['pct'] > 75]
        if not risk_areas:
            risk_areas = ["Shopping", "Food & Dining"]
            
        return {
            "predicted_income": int(predicted_income),
            "predicted_expenses": int(predicted_expenses),
            "risk_areas": risk_areas[:2],
            "outlook": outlook,
            "summary": f"Your next month's cash flow outlook is {outlook}. Projecting savings of ₹{predicted_savings:,.0f} based on a monthly income of ₹{predicted_income:,.0f} and expenses of ₹{predicted_expenses:,.0f}."
        }

    else:  # general
        insights = []
        
        if savings_rate >= 20:
            insights.append({
                "title": "Excellent Savings Rate",
                "description": f"You saved ₹{savings:,.0f} ({savings_rate:.1f}% of income) this month. This outperforms the standard 15% benchmark for the {user.age_group} cohort.",
                "type": "success",
                "priority": "high"
            })
        elif savings_rate > 0:
            insights.append({
                "title": "Increase Savings Velocity",
                "description": f"You saved ₹{savings:,.0f} ({savings_rate:.1f}% of income). For your age group ({user.age_group}), aiming for 20% savings (₹{(income * 0.2):,.0f}) will establish a strong safety margin.",
                "type": "tip",
                "priority": "high"
            })
        else:
            insights.append({
                "title": "Savings Deficit Warning",
                "description": f"Your savings are negative this month (deficit of ₹{abs(savings):,.0f}). Immediate expense reductions in dining/discretionary items are recommended to restore positive cash flow.",
                "type": "alert",
                "priority": "high"
            })
            
        over_budgets = [b for b in budget_details if b['pct'] > 100]
        warn_budgets = [b for b in budget_details if 80 <= b['pct'] <= 100]
        
        if over_budgets:
            insights.append({
                "title": "Budget Limit Exceeded",
                "description": f"You have exceeded your limit in {over_budgets[0]['name']} (spent ₹{over_budgets[0]['spent']:,.0f} vs ₹{over_budgets[0]['limit']:,.0f}). Freeze spending in this category.",
                "type": "warning",
                "priority": "high"
            })
        elif warn_budgets:
            insights.append({
                "title": "Budget Threshold Warning",
                "description": f"Your spending in {warn_budgets[0]['name']} is at {warn_budgets[0]['pct']:.0f}% of its limit (₹{warn_budgets[0]['spent']:,.0f}/{warn_budgets[0]['limit']:,.0f}). Exercise caution for the remainder of the month.",
                "type": "warning",
                "priority": "medium"
            })
        else:
            insights.append({
                "title": "Stable Budget Controls",
                "description": "Outstanding budget discipline! None of your configured category limits have breached the critical 80% threshold this cycle.",
                "type": "success",
                "priority": "medium"
            })
            
        food_spent = stats['category_spending'].get('Food & Dining', 0)
        if food_spent > (income * 0.15):
            insights.append({
                "title": "High Food Velocity",
                "description": f"Food and dining out stands at ₹{food_spent:,.0f} ({food_spent/income*100:.1f}% of your total income). Try meal prepping to lower this block.",
                "type": "warning",
                "priority": "medium"
            })
        else:
            insights.append({
                "title": "Optimized Food Allocation",
                "description": f"Your dining costs are well managed at ₹{food_spent:,.0f} this cycle, keeping food spending within healthy parameters.",
                "type": "success",
                "priority": "low"
            })
            
        if user.age < 25:
            insights.append({
                "title": "Build Career Equity",
                "description": f"At {user.age} years old, your primary financial lever is earning capacity. Allocate a small portion of savings to skills and certifications.",
                "type": "tip",
                "priority": "low"
            })
        elif user.age <= 35:
            insights.append({
                "title": "Automate Equity Allocations",
                "description": f"For the {user.age_group} bracket, automating mutual fund SIPs is ideal. Aim to invest at least 15% of your target ₹{user.monthly_income:,.0f} income.",
                "type": "tip",
                "priority": "medium"
            })
        elif user.age <= 50:
            insights.append({
                "title": "Audit Home & Asset Loans",
                "description": "Peak earning years are ideal for prepaying home loan principals. Even minor lump-sums save lakhs in cumulative interest costs.",
                "type": "tip",
                "priority": "medium"
            })
        else:
            insights.append({
                "title": "Capital Preservation Focus",
                "description": "Gradually shift outstanding mutual fund balances towards debt structures to secure your liquid retirement corpus.",
                "type": "tip",
                "priority": "high"
            })
            
        return insights

@app.route('/api/ai-insights', methods=['POST'])
def api_ai_insights():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'No user found'}), 400

    data = request.json
    insight_type = data.get('type', 'general')
    stats = get_monthly_stats()

    # Fallback to local rule engine if no API key is configured
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        mock_data = get_mock_insights(insight_type, user, stats)
        return jsonify({'success': True, 'data': mock_data, 'type': insight_type})

    try:
        client = Anthropic()
        all_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(50).all()
        tx_summary = []
        for t in all_transactions:
            tx_summary.append({
                'title': t.title,
                'amount': t.amount,
                'type': t.type,
                'category': t.category.name if t.category else 'Other',
                'date': t.date.strftime('%Y-%m-%d')
            })

        budgets = Budget.query.filter_by(month=date.today().month, year=date.today().year).all()
        budget_info = [{'category': b.category.name, 'limit': b.limit_amount, 'spent': stats['category_spending'].get(b.category.name, 0)} for b in budgets]

        prompts = {
            'general': f"""You are a personal finance AI advisor. Analyze this user's financial data and give exactly 4 actionable insights.

User Profile:
- Name: {user.name}
- Age: {user.age} ({user.age_group})
- Monthly Income Target: ₹{user.monthly_income:,.0f}

This Month:
- Total Income: ₹{stats['income']:,.0f}
- Total Expenses: ₹{stats['expenses']:,.0f}
- Net Balance: ₹{stats['balance']:,.0f}
- Category Spending: {json.dumps(stats['category_spending'])}

Recent Transactions (last 50): {json.dumps(tx_summary)}
Budget Status: {json.dumps(budget_info)}

Return ONLY a JSON array with exactly 4 objects. Each object must have:
- "title": short insight title (max 6 words)
- "description": 2-3 sentence explanation with specific numbers
- "type": one of "warning", "success", "tip", "alert"
- "priority": "high", "medium", or "low"

Consider age group {user.age_group} for advice (e.g., retirement planning for older users, student loans/career building for young adults, etc.)
Return only valid JSON, no markdown, no extra text.""",

            'savings': f"""You are a savings advisor. The user is a {user.age}-year-old ({user.age_group}).
Monthly income: ₹{user.monthly_income:,.0f}, expenses this month: ₹{stats['expenses']:,.0f}.
Category breakdown: {json.dumps(stats['category_spending'])}

Give exactly 3 savings recommendations tailored to their age group.
Return ONLY a JSON array with objects having: title, description, potential_saving (number in INR), type ("tip" or "warning").
No markdown, no extra text.""",

            'forecast': f"""You are a financial forecasting AI. Predict next month's finances for this user.
Age: {user.age} ({user.age_group}), Income: ₹{user.monthly_income:,.0f}
Last month expenses: ₹{stats['expenses']:,.0f}
Spending by category: {json.dumps(stats['category_spending'])}
Recent transactions: {json.dumps(tx_summary[:20])}

Return ONLY a JSON object with:
- "predicted_expenses": number
- "predicted_income": number  
- "risk_areas": array of strings (categories likely to overspend)
- "outlook": "positive", "neutral", or "concerning"
- "summary": 2 sentence forecast
No markdown, no extra text."""
        }

        prompt = prompts.get(insight_type, prompts['general'])
        
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw = response.content[0].text.strip()
        parsed = json.loads(raw)
        return jsonify({'success': True, 'data': parsed, 'type': insight_type})
    except Exception as e:
        mock_data = get_mock_insights(insight_type, user, stats)
        return jsonify({'success': True, 'data': mock_data, 'type': insight_type})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_defaults()
    app.run(debug=True, port=5000)
