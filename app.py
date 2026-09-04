"""
ASSIGNMATE - Peer-to-Peer Student Tutoring Marketplace
A platform for students to find verified peer tutors with secure escrow payments.
Aligns with SDG 4 - Quality Education: Promoting inclusive and equitable learning.
Built by Team DETONATORS V4
"""

import sqlite3
import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'assignmate-secure-educational-key-v4')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- DATABASE SETUP ---
# Store all user accounts, task bounties, and escrow transactions in a local SQLite file
DATABASE = 'assignmate.db'

def get_db():
    # Helper to grab a sqlite connection. row_factory = sqlite3.Row lets us access columns
    # like dict keys (row['title']) which makes templating much easier to read
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Creates tables if this is the first time running the project

    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usn TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 1000.0,
                rating_sum REAL DEFAULT 0,
                rating_count INTEGER DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                bounty REAL NOT NULL,
                status TEXT NOT NULL,
                client_id INTEGER,
                freelancer_id INTEGER,
                submission_url TEXT,
                due_date TEXT,
                rating INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(client_id) REFERENCES users(id),
                FOREIGN KEY(freelancer_id) REFERENCES users(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                amount REAL,
                description TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

        # Seed Admin Account
        admin_exists = conn.execute('SELECT id FROM users WHERE usn = ?', ('ADMIN001',)).fetchone()
        if not admin_exists:
            conn.execute('''
                INSERT INTO users (usn, name, role, password_hash, balance, is_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('ADMIN001', 'System Admin', 'ADMIN', generate_password_hash('admin123'), 10000.0, 1))
            conn.commit()
            print("[OK] Admin account created: USN=ADMIN001, Password=admin123")

def seed_dummy_data():
    """Clear all data except admin and seed with dummy data"""
    with get_db() as conn:
        # Clear existing data (except admin)
        conn.execute('DELETE FROM transactions')
        conn.execute('DELETE FROM tasks')
        conn.execute('DELETE FROM users WHERE role != "ADMIN"')
        conn.commit()

        # Dummy Learners (they request tutoring)
        students = [
            ('1RV23CS001', 'Arjun Sharma', 'LEARNER', 'pass123', 1500.0),
            ('1RV23CS045', 'Priya Patel', 'LEARNER', 'pass123', 2000.0),
            ('1RV23ME017', 'Rahul Verma', 'LEARNER', 'pass123', 800.0),
            ('1RV23EC032', 'Sneha Reddy', 'LEARNER', 'pass123', 1200.0),
        ]

        # Dummy Tutors (verified peer tutors)
        helpers = [
            ('1RV22CS099', 'Vikram Singh', 'TUTOR', 'pass123', 3500.0, 4.5, 12),
            ('1RV22IS028', 'Ananya Krishnan', 'TUTOR', 'pass123', 2800.0, 4.8, 8),
            ('1RV21CS055', 'Karthik Nair', 'TUTOR', 'pass123', 5200.0, 4.2, 20),
        ]

        student_ids = []
        helper_ids = []

        for usn, name, role, pwd, balance in students:
            cur = conn.execute('''
                INSERT INTO users (usn, name, role, password_hash, balance, is_verified)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (usn, name, role, generate_password_hash(pwd), balance))
            student_ids.append(cur.lastrowid)

        for usn, name, role, pwd, balance, rating, count in helpers:
            cur = conn.execute('''
                INSERT INTO users (usn, name, role, password_hash, balance, is_verified, rating_sum, rating_count)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ''', (usn, name, role, generate_password_hash(pwd), balance, rating * count, count))
            helper_ids.append(cur.lastrowid)

        # Dummy Tutoring Sessions with various statuses
        tasks = [
            # OPEN tutoring requests
            (student_ids[0], None, 'Python Basics - Data Structures',
             'Need help understanding lists, dictionaries, and tuples in Python. Struggling with when to use each one.',
             250.0, 'OPEN', None, '2026-01-25'),

            (student_ids[1], None, 'React Fundamentals Tutoring',
             'Looking for a tutor to explain React hooks (useState, useEffect) and component lifecycle. Need hands-on practice.',
             500.0, 'OPEN', None, '2026-01-28'),

            (student_ids[3], None, 'Database Concepts - ER Diagrams',
             'Need tutoring on how to design ER diagrams. Confused about relationships, cardinality, and normalization.',
             150.0, 'OPEN', None, '2026-01-22'),

            # ASSIGNED sessions (tutor accepted)
            (student_ids[0], helper_ids[0], 'Machine Learning Concepts',
             'Need help understanding classification algorithms like Decision Trees and KNN. Want to learn the intuition.',
             350.0, 'ASSIGNED', None, '2026-01-30'),

            (student_ids[2], helper_ids[1], 'Web Development Basics',
             'Need guidance on how HTML, CSS, and JavaScript work together. Want to build my first webpage.',
             400.0, 'ASSIGNED', None, '2026-02-01'),

            # SUBMITTED sessions (tutoring completed, pending approval)
            (student_ids[1], helper_ids[2], 'UI/UX Design Principles',
             'Learned about color theory, typography, and layout design. Tutor shared resources and examples.',
             300.0, 'SUBMITTED', 'https://drive.google.com/file/d/session-notes-uiux/SharedNotes.pdf', '2026-01-20'),

            (student_ids[3], helper_ids[0], 'Java OOP Concepts Session',
             'Covered inheritance, polymorphism, and interfaces with coding examples. Cleared all my doubts.',
             200.0, 'SUBMITTED', 'https://github.com/demo-user/java-oop-notes/archive/main.zip', '2026-01-19'),

            # COMPLETED sessions (approved and paid)
            (student_ids[0], helper_ids[1], 'SQL Fundamentals Tutoring',
             'Learned JOIN operations, subqueries, and basic database design. Now confident with SQL basics.',
             275.0, 'COMPLETED', 'https://drive.google.com/file/d/sql-session-notes/SQLNotes.pdf', '2026-01-15'),

            (student_ids[2], helper_ids[2], 'Presentation Skills Workshop',
             'Got tips on slide design, storytelling, and public speaking. Very helpful session!',
             180.0, 'COMPLETED', 'https://docs.google.com/presentation/d/1xyz789/PresentationTips.pptx', '2026-01-12'),
        ]

        for client_id, freelancer_id, title, desc, bounty, status, submission, due_date in tasks:
            conn.execute('''
                INSERT INTO tasks (client_id, freelancer_id, title, description, bounty, status, submission_url, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (client_id, freelancer_id, title, desc, bounty, status, submission, due_date))

        # Add some transactions
        transactions = [
            (student_ids[0], 'DEBIT', 250.0, 'Booked: Python Basics Tutoring'),
            (student_ids[1], 'DEBIT', 500.0, 'Booked: React Fundamentals Tutoring'),
            (helper_ids[1], 'CREDIT', 275.0, 'Session Completed: SQL Fundamentals'),
            (helper_ids[2], 'CREDIT', 180.0, 'Session Completed: Presentation Skills'),
            (student_ids[0], 'DEBIT', 350.0, 'Booked: ML Concepts Tutoring'),
        ]

        for user_id, tx_type, amount, desc in transactions:
            conn.execute('''
                INSERT INTO transactions (user_id, type, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, tx_type, amount, desc))

        conn.commit()
        print("[OK] Dummy data seeded successfully!")
        print("   - 4 Learners (password: pass123)")
        print("   - 3 Tutors (password: pass123)")
        print("   - 9 Tutoring Sessions (various statuses)")
        print("   - Sample transactions")

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to continue.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user['role'] != 'ADMIN':
            flash("Access denied. Admin privileges required.")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the currently logged in user"""
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

def render_nav(user, active_page):
    """Render the navigation sidebar with user context"""
    nav_html = f'''
    <div class="sidebar">
        <div class="logo">📖 ASSIGNMATE</div>
        <nav>
            <a href="/" class="nav-link {'active' if active_page == 'dashboard' else ''}">📊 Dashboard</a>
            <a href="/profile" class="nav-link {'active' if active_page == 'profile' else ''}">👤 My Profile</a>
            <a href="/my-tasks" class="nav-link {'active' if active_page == 'my_tasks' else ''}">📝 My Tasks</a>
            <a href="/settings" class="nav-link {'active' if active_page == 'settings' else ''}">⚙️ Settings</a>
            {'<a href="/admin" class="nav-link ' + ('active' if active_page == 'admin' else '') + '">🛡️ Admin Panel</a>' if user['role'] == 'ADMIN' else ''}
        </nav>

        <div style="margin-top: 2rem; padding: 1.5rem; background: var(--primary-light); border-radius: 1.25rem; border: 1px solid rgba(16, 185, 129, 0.15);">
            <p style="font-size: 0.7rem; color: var(--primary); text-transform: uppercase; font-weight: 800; margin-bottom: 0.5rem; letter-spacing: 0.05em;">Role Identity</p>
            <p style="font-weight: 800; color: var(--text-main); font-size: 1rem; font-family: 'Outfit';">{user['role']}</p>
        </div>

        <a href="/logout" class="nav-link logout">🚪 Logout</a>
    </div>
    <div class="watermark">🚀 Crafted by Team <span>DETONATORS V4</span></div>
    '''
    return nav_html

# --- CSS & TEMPLATES ---
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
    --primary: #10B981;
    --primary-hover: #059669;
    --primary-light: rgba(16, 185, 129, 0.08);
    --primary-glow: rgba(16, 185, 129, 0.15);
    --bg: #F0FDF4;
    --card: #FFFFFF;
    --text-main: #111827;
    --text-muted: #6B7280;
    --border: rgba(0, 0, 0, 0.06);
    --success: #10B981;
    --danger: #EF4444;
    --warning: #F59E0B;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
    --shadow-glow: 0 0 40px rgba(16, 185, 129, 0.15);
    --glass: rgba(255, 255, 255, 0.9);
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 50%, #D1FAE5 100%);
    background-attachment: fixed;
    color: var(--text-main);
    font-family: 'Plus Jakarta Sans', sans-serif;
    min-height: 100vh;
    display: flex;
    -webkit-font-smoothing: antialiased;
}

h1, h2, h3, .logo { font-family: 'Outfit', sans-serif; }

.animate-fadeIn { animation: fadeIn 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards; }

/* Sidebar */
.sidebar {
    width: 270px;
    background: var(--glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-right: 1px solid rgba(16, 185, 129, 0.1);
    padding: 2.5rem 1.5rem;
    display: flex;
    flex-direction: column;
    position: fixed;
    height: 100vh;
    z-index: 100;
    box-shadow: 4px 0 30px rgba(0, 0, 0, 0.03);
}

.logo {
    font-size: 1.7rem;
    font-weight: 800;
    color: var(--primary);
    margin-bottom: 3.5rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    letter-spacing: -0.03em;
    text-shadow: 0 2px 10px rgba(16, 185, 129, 0.2);
}

.nav-link {
    display: flex;
    align-items: center;
    padding: 0.9rem 1.25rem;
    color: var(--text-muted);
    text-decoration: none;
    border-radius: 1rem;
    margin-bottom: 0.5rem;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid transparent;
}

.nav-link:hover {
    background: var(--primary-light);
    color: var(--primary);
    transform: translateX(6px);
    border-color: rgba(16, 185, 129, 0.15);
}

.nav-link.active {
    background: linear-gradient(135deg, var(--primary) 0%, #059669 100%);
    color: white;
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35);
    border-color: transparent;
}

.nav-link.logout { margin-top: auto; color: var(--danger); }
.nav-link.logout:hover { background: #FEF2F2; color: var(--danger); border-color: rgba(239, 68, 68, 0.15); }

/* Main Area */
.main {
    margin-left: 270px;
    flex: 1;
    padding: 3rem 4rem 6rem;
    max-width: 1400px;
    min-height: 100vh;
}

.card {
    background: var(--card);
    border-radius: 1.5rem;
    padding: 2rem;
    box-shadow: var(--shadow-sm);
    margin-bottom: 1.5rem;
    border: 1px solid rgba(16, 185, 129, 0.08);
    transition: all 0.3s ease;
}
.card:hover {
    box-shadow: var(--shadow);
    transform: translateY(-2px);
    border-color: rgba(16, 185, 129, 0.15);
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin-bottom: 2.5rem;
}

.stat-card {
    padding: 1.75rem;
    border-radius: 1.5rem;
    background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 100%);
    border: 1px solid rgba(16, 185, 129, 0.1);
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.08);
    transition: all 0.3s ease;
}
.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.15);
}
.stat-label { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
.stat-value { font-size: 2rem; font-weight: 800; color: var(--primary); font-family: 'Outfit'; }

/* Badges */
.badge {
    padding: 0.45rem 0.9rem;
    border-radius: 2rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.badge-OPEN { background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%); color: #065F46; }
.badge-ASSIGNED { background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%); color: #B45309; }
.badge-SUBMITTED { background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%); color: #4338CA; }
.badge-COMPLETED { background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: white; box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3); }
.badge-FAILED { background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%); color: #B91C1C; }

input, select, textarea {
    width: 100%;
    padding: 0.85rem 1.15rem;
    border: 2px solid rgba(16, 185, 129, 0.15);
    border-radius: 1rem;
    margin-top: 0.5rem;
    font-family: inherit;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    background: rgba(240, 253, 244, 0.5);
}
input:focus, select:focus, textarea:focus {
    border-color: var(--primary);
    outline: none;
    background: white;
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.1);
}

button {
    padding: 0.85rem 1.75rem;
    border-radius: 1rem;
    background: linear-gradient(135deg, var(--primary) 0%, #059669 100%);
    color: white;
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    border: none;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.25);
}
button:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.35);
}
button:active { transform: translateY(-1px); }

.btn-outline {
    background: transparent;
    border: 2px solid rgba(16, 185, 129, 0.2);
    color: var(--text-main);
    box-shadow: none;
}
.btn-outline:hover {
    background: var(--primary-light);
    border-color: var(--primary);
    color: var(--primary);
}

/* Table */
table { width: 100%; border-collapse: separate; border-spacing: 0 0.6rem; margin-top: 1rem; }
th { text-align: left; padding: 1rem 1.25rem; font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; }
td { padding: 1.35rem 1.25rem; background: white; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
td:first-child { border-left: 1px solid var(--border); border-radius: 1rem 0 0 1rem; }
td:last-child { border-right: 1px solid var(--border); border-radius: 0 1rem 1rem 0; }
tr:hover td { background: #F0FDF4; }

.text-success { color: var(--success); font-weight: 700; }
.text-danger { color: var(--danger); font-weight: 700; }

.alert {
    padding: 1.25rem 1.5rem;
    background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
    color: #065F46;
    border-radius: 1rem;
    margin-bottom: 2rem;
    font-weight: 600;
    border-left: 5px solid var(--primary);
    animation: fadeIn 0.5s ease-out;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.1);
}

/* Watermark Footer */
.watermark {
    position: fixed;
    bottom: 0;
    left: 270px;
    right: 0;
    text-align: center;
    padding: 1rem;
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(5, 150, 105, 0.08) 100%);
    backdrop-filter: blur(8px);
    border-top: 1px solid rgba(16, 185, 129, 0.1);
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--primary);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-family: 'Outfit', sans-serif;
    z-index: 50;
}
.watermark span {
    background: linear-gradient(90deg, #10B981, #059669, #10B981);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 3s linear infinite;
}
"""

AUTH_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASSIGNMATE - {{ mode }}</title>
    <style>{{ css }}</style>
    <style>
        body { justify-content: center; align-items: center; background: #F0F2F5; }
        .auth-card {
            width: 100%;
            max-width: 420px;
            background: white;
            padding: 3.5rem;
            border-radius: 2rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
            animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .auth-header { text-align: center; margin-bottom: 3rem; }
        .auth-header h2 { font-size: 1.75rem; color: #111827; margin-top: 0.5rem; font-weight: 800; letter-spacing: -0.02em; }
    </style>
</head>
<body>
    <div class="auth-card">
        <div class="auth-header">
            <div class="logo" style="justify-content: center; margin: 0; font-size: 2.25rem;">📖 ASSIGNMATE</div>
            <h2>{{ mode }}</h2>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}{% for m in messages %}<div class="alert" style="padding: 0.75rem; font-size: 0.85rem;">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}

        <form method="POST">
            {% if mode == 'Register' %}
            <div style="margin-bottom: 1.5rem;">
                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Full Name</label>
                <input type="text" name="name" placeholder="Zoro" required>
            </div>
            <div style="margin-bottom: 1.5rem;">
                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Role</label>
                <select name="role">
                    <option value="LEARNER">Learner (I need tutoring)</option>
                    <option value="TUTOR">Tutor (I help peers learn)</option>
                </select>
            </div>
            {% endif %}
            <div style="margin-bottom: 1.5rem;">
                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">University USN</label>
                <input type="text" name="usn" placeholder="e.g. 1RV23CS001" required>
            </div>
            <div style="margin-bottom: 2.5rem;">
                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">Password</label>
                <input type="password" name="password" placeholder="••••••••" required>
            </div>
            <button type="submit" style="width: 100%; padding: 1.1rem; font-size: 1rem;">{{ mode }}</button>
        </form>

        <p style="text-align: center; margin-top: 2.5rem; font-size: 0.95rem; color: var(--text-muted); font-weight: 500;">
            {% if mode == 'Login' %}
            New here? <a href="{{ url_for('register') }}" style="color: var(--primary); font-weight: 800; text-decoration: none;">Join the Hub</a>
            {% else %}
            Already a member? <a href="{{ url_for('login') }}" style="color: var(--primary); font-weight: 800; text-decoration: none;">Sign In</a>
            {% endif %}
        </p>
    </div>
</body>
</html>
"""

NAV_PARTIAL = """
<div class="sidebar">
    <div class="logo">📖 ASSIGNMATE</div>
    <nav>
        <a href="/" class="nav-link {{ 'active' if active_page == 'dashboard' else '' }}">📊 Dashboard</a>
        <a href="/profile" class="nav-link {{ 'active' if active_page == 'profile' else '' }}">👤 My Profile</a>
        <a href="/my-tasks" class="nav-link {{ 'active' if active_page == 'my_tasks' else '' }}">📝 My Tasks</a>
        <a href="/settings" class="nav-link {{ 'active' if active_page == 'settings' else '' }}">⚙️ Settings</a>
    </nav>

    <div style="margin-top: 2rem; padding: 1.5rem; background: var(--primary-light); border-radius: 1.25rem; border: 1px solid rgba(16, 185, 129, 0.15);">
        <p style="font-size: 0.7rem; color: var(--primary); text-transform: uppercase; font-weight: 800; margin-bottom: 0.5rem; letter-spacing: 0.05em;">Role Identity</p>
        <p style="font-weight: 800; color: var(--text-main); font-size: 1rem; font-family: 'Outfit';">{{ user.role }}</p>
    </div>

    <a href="/logout" class="nav-link logout">🚪 Logout</a>
</div>
<div class="watermark">🚀 Crafted by Team <span>DETONATORS V4</span></div>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASSIGNMATE - Dashboard</title>
    <style>{{ css }}</style>
</head>
<body>
    {{ nav_partial | safe }}

    <div class="main">
        <div class="animate-fadeIn">
            <!-- Unified Landing Header -->
            <div style="margin-bottom: 3.5rem; display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <h1 style="font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;">Activity Dashboard</h1>
                    <p style="color: var(--text-muted); font-size: 1.1rem; margin-top: 0.4rem; font-weight: 500;">Welcome back, <span style="color: var(--primary); font-weight: 700;">{{ user.name }}</span></p>
                </div>
                <div style="text-align: right;">
                    <p style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem;">Wallet Balance</p>
                    <div style="font-size: 2.75rem; font-weight: 800; color: var(--primary); line-height: 1; font-family: 'Outfit';">₹{{ "%.2f"|format(user.balance) }}</div>
                </div>
            </div>

            {% with messages = get_flashed_messages() %}
                {% if messages %}{% for m in messages %}<div class="alert">🚀 {{ m }}</div>{% endfor %}{% endif %}
            {% endwith %}

            <!-- Performance Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Active Gigs</div>
                    <div class="stat-value">{{ active_count }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Successful Deliveries</div>
                    <div class="stat-value">{{ completed_count }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Community Rating</div>
                    <div class="stat-value" style="color: #F59E0B;">
                        {% if user.rating_count > 0 %}
                            {{ "%.1f"|format(user.rating_sum/user.rating_count) }} <span style="font-size: 1rem;">★</span>
                        {% else %}
                            <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 600;">NEW JOINER</span>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 400px; gap: 4rem; align-items: start;">
                <!-- Marketplace Discovery Area -->
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                        <h2 style="font-size: 1.75rem; font-weight: 800; letter-spacing: -0.02em;">Project Discovery</h2>
                        <form action="/" method="GET" style="width: 320px;">
                            <input type="text" name="q" placeholder="🔍 Search tasks..." value="{{ request.args.get('q', '') }}" style="margin: 0; background: white; border-radius: 2rem; border: 1px solid rgba(0,0,0,0.1);">
                        </form>
                    </div>

                    {% for task in tasks %}
                    <div class="card" style="padding: 2rem; margin-bottom: 1.5rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem;">
                                    <span class="badge badge-{{ task.status }}">{{ task.status }}</span>
                                    {% if task.due_date %}
                                    <span style="font-size: 0.8rem; font-weight: 800; color: #F59E0B; background: #FFFBEB; padding: 0.3rem 0.6rem; border-radius: 0.5rem;">📅 Due: {{ task.due_date }}</span>
                                    {% endif %}
                                </div>
                                <h3 style="font-size: 1.4rem; font-weight: 800; margin-bottom: 0.75rem; letter-spacing: -0.01em;">{{ task.title }}</h3>
                                <p style="color: var(--text-muted); font-size: 1rem; line-height: 1.6; margin-bottom: 2rem;">{{ task.description }}</p>

                                <div style="display: flex; align-items: center; gap: 1rem;">
                                    {% if user['role'] == 'TUTOR' and task.status == 'OPEN' %}
                                        <form action="{{ url_for('take_task', task_id=task.id) }}" method="POST"><button type="submit">Accept Tutoring Request</button></form>
                                    {% elif task.freelancer_id == user['id'] and task.status == 'ASSIGNED' %}
                                        <form action="{{ url_for('submit_job', task_id=task.id) }}" method="POST" style="display: flex; flex-direction: column; gap: 0.75rem; flex: 1;">
                                            <input type="text" name="submission" placeholder="📎 Share session notes link (Google Drive, Notion, etc.)" required style="margin: 0;">
                                            <button type="submit" style="align-self: flex-start;">📤 Mark Session Complete</button>
                                        </form>
                                        <!-- Session Notes Preview -->
                                        <div style="background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%); padding: 1.25rem; border-radius: 1rem; margin-bottom: 1rem; border: 1px solid rgba(16, 185, 129, 0.2);">
                                            <p style="font-size: 0.7rem; font-weight: 800; color: #065F46; text-transform: uppercase; margin-bottom: 0.5rem;">📎 Session Notes</p>
                                            <a href="{{ task.submission_url }}" target="_blank" style="color: #047857; font-weight: 700; word-break: break-all; text-decoration: underline;">{{ task.submission_url }}</a>
                                        </div>
                                        <form action="{{ url_for('approve_job', task_id=task.id) }}" method="POST" style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                                            <select name="rating" style="width: auto; margin:0;" required>
                                                <option value="5">⭐ Excellent (5)</option>
                                                <option value="4">👍 Good (4)</option>
                                                <option value="3">👌 Average (3)</option>
                                                <option value="2">👎 Below Average (2)</option>
                                                <option value="1">❌ Poor (1)</option>
                                            </select>
                                            <button type="submit">✅ Approve & Release Payment</button>
                                        </form>
                                    {% endif %}

                                    {% if task.client_id == user['id'] and task.status == 'OPEN' %}
                                         <form action="{{ url_for('cancel_job', task_id=task.id) }}" method="POST"><button type="submit" class="btn-outline">Withdraw</button></form>
                                    {% endif %}
                                </div>
                            </div>
                            <div style="text-align: right; margin-left: 2.5rem;">
                                <div style="font-size: 1.75rem; font-weight: 800; color: var(--primary); font-family: 'Outfit';">₹{{ "%.0f"|format(task.bounty) }}</div>
                                <p style="font-size: 0.7rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Requested by {{ task.client_name }}</p>
                            </div>
                        </div>
                    </div>
                    {% else %}
                    <div style="text-align: center; padding: 6rem; background: rgba(0,0,0,0.02); border-radius: 2rem; border: 2px dashed rgba(0,0,0,0.05);">
                        <div style="font-size: 3rem; margin-bottom: 1.5rem;">🔭</div>
                        <h3 style="color: var(--text-main); margin-bottom: 0.5rem;">No tutoring requests found</h3>
                        <p style="color: var(--text-muted); font-weight: 500;">Try a different search term or check back later.</p>
                    </div>
                    {% endfor %}
                </div>

                <!-- Strategic Action Sidebar -->
                <div style="position: sticky; top: 3rem;">
                    {% if user['role'] in ['LEARNER', 'ADMIN'] %}
                    <div class="card" style="border: none; background: #111827; color: white;">
                        <h2 style="font-size: 1.4rem; margin-bottom: 1.75rem; font-weight: 800; color: white;">Request Tutoring</h2>
                        <form action="/post_task" method="POST">
                            <label style="font-size: 0.7rem; font-weight: 800; color: rgba(255,255,255,0.5); text-transform: uppercase;">Subject / Topic</label>
                            <input type="text" name="title" placeholder="e.g. Python Basics" required style="margin-bottom: 1.5rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;">

                            <label style="font-size: 0.7rem; font-weight: 800; color: rgba(255,255,255,0.5); text-transform: uppercase;">What do you need help with?</label>
                            <textarea name="description" rows="4" placeholder="Describe what concepts you're struggling with..." required style="margin-bottom: 1.5rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;"></textarea>

                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem;">
                                <div>
                                    <label style="font-size: 0.7rem; font-weight: 800; color: rgba(255,255,255,0.5); text-transform: uppercase;">Session Fee (₹)</label>
                                    <input type="number" name="bounty" required style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;">
                                </div>
                                <div>
                                    <label style="font-size: 0.7rem; font-weight: 800; color: rgba(255,255,255,0.5); text-transform: uppercase;">Preferred Date</label>
                                    <input type="date" name="due_date" required style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;">
                                </div>
                            </div>
                            <button type="submit" style="width: 100%; padding: 1.1rem; background: var(--primary);">Request Tutoring Session</button>
                        </form>
                    </div>
                    {% endif %}

                    <div class="card" style="background: var(--primary-light); border: 1px solid rgba(79, 70, 229, 0.1); text-align: center; padding: 2.5rem;">
                        <div style="font-size: 2.5rem; margin-bottom: 1.25rem;">🛡️</div>
                        <h3 style="font-size: 1.25rem; font-weight: 800; color: var(--primary); margin-bottom: 0.75rem;">Escrow Protection</h3>
                        <p style="font-size: 0.95rem; color: #4338CA; opacity: 0.8; line-height: 1.6; font-weight: 500;">Funds are held securely by ASSIGNMATE until you approve the work.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="watermark">🚀 Crafted by Team <span>DETONATORS V4</span></div>
</body>
</html>
"""

PROFILE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASSIGNMATE - Profile</title>
    <style>{{ css }}</style>
</head>
<body>
    {{ nav_partial | safe }}

    <div class="main">
        <div class="animate-fadeIn">
            <div style="margin-bottom: 3.5rem;">
                <h1 style="font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;">User Profile</h1>
                <p style="color: var(--text-muted); font-size: 1.1rem; margin-top: 0.4rem; font-weight: 500;">Manage your identity and history</p>
            </div>

            <div style="display: grid; grid-template-columns: 400px 1fr; gap: 4rem; align-items: start;">
                <!-- Profile Identity Card -->
                <div class="card" style="text-align: center; padding: 3rem 2rem;">
                    <div style="width: 100px; height: 100px; background: var(--primary); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; font-weight: 800; margin: 0 auto 1.5rem; font-family: 'Outfit'; shadow: 0 10px 20px rgba(79, 70, 229, 0.2);">
                        {{ user.name[0] }}
                    </div>
                    <h2 style="font-size: 1.75rem; margin-bottom: 0.5rem;">{{ user.name }}</h2>
                    <p style="color: var(--text-muted); font-weight: 600; font-size: 0.95rem; margin-bottom: 2rem;">{{ user.usn }}</p>

                    <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem;">
                        <span class="badge" style="background: var(--primary-light); color: var(--primary); font-size: 0.8rem; padding: 0.5rem 1rem;">{{ user.role }}</span>
                        {% if user.is_verified %}
                            <span class="badge" style="background: #D1FAE5; color: #065F46; font-size: 0.8rem; padding: 0.5rem 1rem;">VERIFIED</span>
                        {% endif %}
                    </div>

                    <div style="margin-top: 2.5rem; padding-top: 2rem; border-top: 1px solid var(--border); display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div>
                            <p style="font-size: 0.7rem; color: var(--text-muted); font-weight: 800; text-transform: uppercase;">Rating</p>
                            <p style="font-weight: 800; font-size: 1.25rem; color: #F59E0B; font-family: 'Outfit';">
                                {% if user.rating_count > 0 %}{{ "%.1f"|format(user.rating_sum/user.rating_count) }}<span style="font-size: 0.8rem; margin-left: 2px;">★</span>{% else %}NEW{% endif %}
                            </p>
                        </div>
                        <div>
                            <p style="font-size: 0.7rem; color: var(--text-muted); font-weight: 800; text-transform: uppercase;">Since</p>
                            <p style="font-weight: 800; font-size: 1.25rem; color: var(--text-main); font-family: 'Outfit';">2024</p>
                        </div>
                    </div>
                </div>

                <!-- Transaction History -->
                <div>
                    <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem; letter-spacing: -0.02em;">Recent Transactions</h2>
                    <div class="card" style="padding: 1rem;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Activity Details</th>
                                    <th>Date</th>
                                    <th style="text-align: right;">Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for tx in transactions %}
                                <tr>
                                    <td style="font-weight: 700; color: var(--text-main);">{{ tx.description }}</td>
                                    <td style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">{{ tx.timestamp.split(' ')[0] }}</td>
                                    <td style="text-align: right;" class="{{ 'text-success' if tx.type == 'CREDIT' else 'text-danger' }}">
                                        <span style="font-family: 'Outfit'; font-weight: 800; font-size: 1.15rem;">{{ '+' if tx.type == 'CREDIT' else '-' }}₹{{ tx.amount }}</span>
                                    </td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td colspan="3" style="text-align: center; padding: 4rem; color: var(--text-muted); font-weight: 500;">No recent wallet activity found.</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- LOGIC ---

@app.before_request
def before_request():
    init_db()

def get_current_user():
    if 'user_id' not in session: return None
    with get_db() as conn:
        return conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

@app.route('/')
def dashboard():
    user = get_current_user()
    if not user: return redirect(url_for('login'))

    q = request.args.get('q', '')

    with get_db() as conn:
        query = '''
            SELECT t.*, u_c.name as client_name, u_f.name as freelancer_name
            FROM tasks t
            JOIN users u_c ON t.client_id = u_c.id
            LEFT JOIN users u_f ON t.freelancer_id = u_f.id
            WHERE (t.title LIKE ? OR t.description LIKE ?)
            ORDER BY t.status='OPEN' DESC, t.id DESC
        '''
        tasks = conn.execute(query, (f'%{q}%', f'%{q}%')).fetchall()

        active = conn.execute('SELECT COUNT(*) FROM tasks WHERE status IN ("OPEN", "ASSIGNED", "SUBMITTED")').fetchone()[0]
        completed = conn.execute('SELECT COUNT(*) FROM tasks WHERE status="COMPLETED"').fetchone()[0]

    return render_template_string(DASHBOARD_TEMPLATE, user=user, tasks=tasks, active_count=active, completed_count=completed, active_page='dashboard', css=BASE_CSS, nav_partial=render_nav(user, 'dashboard'))

@app.route('/profile')
def profile():
    user = get_current_user()
    if not user: return redirect(url_for('login'))
    with get_db() as conn:
        transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10', (user['id'],)).fetchall()
    return render_template_string(PROFILE_TEMPLATE, user=user, transactions=transactions, active_page='profile', css=BASE_CSS, nav_partial=render_nav(user, 'profile'))

@app.route('/my-tasks')
def my_tasks():
    user = get_current_user()
    if not user: return redirect(url_for('login'))

    with get_db() as conn:
        # Tasks posted by user (as client)
        posted_tasks = conn.execute('''
            SELECT t.*, u_f.name as freelancer_name
            FROM tasks t
            LEFT JOIN users u_f ON t.freelancer_id = u_f.id
            WHERE t.client_id = ?
            ORDER BY t.id DESC
        ''', (user['id'],)).fetchall()

        # Tasks assigned to user (as helper)
        assigned_tasks = conn.execute('''
            SELECT t.*, u_c.name as client_name
            FROM tasks t
            JOIN users u_c ON t.client_id = u_c.id
            WHERE t.freelancer_id = ?
            ORDER BY t.id DESC
        ''', (user['id'],)).fetchall()

    MY_TASKS_TEMPLATE = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ASSIGNMATE - My Tasks</title>
        <style>{{ css }}</style>
    </head>
    <body>
        {{ nav_partial | safe }}
        <div class="main">
            <div class="animate-fadeIn">
                <div style="margin-bottom: 3.5rem;">
                    <h1 style="font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;">My Tasks</h1>
                    <p style="color: var(--text-muted); font-size: 1.1rem; margin-top: 0.4rem; font-weight: 500;">All your posted and assigned work</p>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3rem;">
                    <!-- Posted Tasks -->
                    <div>
                        <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem;">📤 Tasks I Posted</h2>
                        {% for task in posted_tasks %}
                        <div class="card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <span class="badge badge-{{ task.status }}">{{ task.status }}</span>
                                    <h3 style="margin-top: 0.75rem; font-weight: 700;">{{ task.title }}</h3>
                                    <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem;">{{ task.description[:100] }}...</p>
                                    {% if task.freelancer_name %}
                                    <p style="margin-top: 0.75rem; font-size: 0.85rem;"><strong>Assigned to:</strong> {{ task.freelancer_name }}</p>
                                    {% endif %}
                                </div>
                                <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary);">₹{{ task.bounty }}</div>
                            </div>
                        </div>
                        {% else %}
                        <div class="card" style="text-align: center; padding: 3rem; color: var(--text-muted);">No tasks posted yet.</div>
                        {% endfor %}
                    </div>

                    <!-- Assigned Tasks -->
                    <div>
                        <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem;">📥 Tasks Assigned to Me</h2>
                        {% for task in assigned_tasks %}
                        <div class="card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <span class="badge badge-{{ task.status }}">{{ task.status }}</span>
                                    <h3 style="margin-top: 0.75rem; font-weight: 700;">{{ task.title }}</h3>
                                    <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem;">{{ task.description[:100] }}...</p>
                                    <p style="margin-top: 0.75rem; font-size: 0.85rem;"><strong>Client:</strong> {{ task.client_name }}</p>
                                </div>
                                <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary);">₹{{ task.bounty }}</div>
                            </div>
                        </div>
                        {% else %}
                        <div class="card" style="text-align: center; padding: 3rem; color: var(--text-muted);">No tasks assigned to you yet.</div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(MY_TASKS_TEMPLATE, user=user, posted_tasks=posted_tasks, assigned_tasks=assigned_tasks, active_page='my_tasks', css=BASE_CSS, nav_partial=render_nav(user, 'my_tasks'))

@app.route('/settings')
def settings():
    user = get_current_user()
    if not user: return redirect(url_for('login'))

    SETTINGS_TEMPLATE = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ASSIGNMATE - Settings</title>
        <style>{{ css }}</style>
    </head>
    <body>
        {{ nav_partial | safe }}
        <div class="main">
            <div class="animate-fadeIn">
                <div style="margin-bottom: 3.5rem;">
                    <h1 style="font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;">Settings</h1>
                    <p style="color: var(--text-muted); font-size: 1.1rem; margin-top: 0.4rem; font-weight: 500;">Manage your account preferences</p>
                </div>

                <div style="max-width: 600px;">
                    <div class="card">
                        <h2 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1.5rem;">Account Information</h2>
                        <div style="display: grid; gap: 1.5rem;">
                            <div>
                                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Full Name</label>
                                <input type="text" value="{{ user.name }}" disabled style="opacity: 0.7;">
                            </div>
                            <div>
                                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">University USN</label>
                                <input type="text" value="{{ user.usn }}" disabled style="opacity: 0.7;">
                            </div>
                            <div>
                                <label style="font-size: 0.75rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Role</label>
                                <input type="text" value="{{ user.role }}" disabled style="opacity: 0.7;">
                            </div>
                        </div>
                    </div>

                    <div class="card" style="background: var(--primary-light); border: 1px solid rgba(16, 185, 129, 0.15);">
                        <h2 style="font-size: 1.25rem; font-weight: 800; color: var(--primary); margin-bottom: 1rem;">💡 Coming Soon</h2>
                        <p style="color: var(--text-muted); line-height: 1.6;">Password change, email notifications, and account deletion features are under development.</p>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(SETTINGS_TEMPLATE, user=user, active_page='settings', css=BASE_CSS, nav_partial=render_nav(user, 'settings'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usn = request.form['usn']
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE usn = ?', (usn,)).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                return redirect(url_for('dashboard'))
            flash("Invalid USN or Password.")
    return render_template_string(AUTH_TEMPLATE, mode='Login', css=BASE_CSS)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usn = request.form['usn']
        name = request.form['name']
        role = request.form['role']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                cur = conn.execute('INSERT INTO users (usn, name, role, password_hash) VALUES (?, ?, ?, ?)', (usn, name, role, hashed_pw))
                conn.commit()
                session['user_id'] = cur.lastrowid
                return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            flash("USN already registered.")
    return render_template_string(AUTH_TEMPLATE, mode='Register', css=BASE_CSS)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/post_task', methods=['POST'])
def post_task():
    user = get_current_user()
    if user['role'] not in ['LEARNER', 'ADMIN']:
        flash("Only Learners can request tutoring sessions.")
        return redirect(url_for('dashboard'))

    title = request.form['title']
    description = request.form['description']
    bounty = float(request.form['bounty'])
    due_date = request.form.get('due_date')

    if user['balance'] >= bounty:
        with get_db() as conn:
            conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (bounty, user['id']))
            conn.execute('INSERT INTO tasks (title, description, bounty, status, client_id, due_date) VALUES (?, ?, ?, "OPEN", ?, ?)',
                         (title, description, bounty, user['id'], due_date))
            conn.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "DEBIT", ?, ?)',
                         (user['id'], bounty, f"Booked tutoring: {title}"))
            conn.commit()
            flash("Tutoring request posted! Fee locked in Safe Deposit.")
    else:
        flash("Insufficient wallet balance.")
    return redirect(url_for('dashboard'))

@app.route('/take_task/<int:task_id>', methods=['POST'])
def take_task(task_id):
    user = get_current_user()
    if user['role'] != 'TUTOR':
        flash("Only Tutors can accept tutoring requests.")
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task and task['status'] == 'OPEN' and task['client_id'] != user['id']:
            conn.execute('UPDATE tasks SET status = "ASSIGNED", freelancer_id = ? WHERE id = ?', (user['id'], task_id))
            conn.commit()
            flash("Tutoring session accepted! You can now schedule with the learner.")
        else:
            flash("Unauthorized or Project unavailable.")
    return redirect(url_for('dashboard'))

@app.route('/submit_job/<int:task_id>', methods=['POST'])
def submit_job(task_id):
    user = get_current_user()
    sub = request.form['submission']
    with get_db() as conn:
        conn.execute('UPDATE tasks SET status = "SUBMITTED", submission_url = ? WHERE id = ? AND freelancer_id = ?',
                     (sub, task_id, user['id']))
        conn.commit()
        flash("Work Submitted! Waiting for owner approval.")
    return redirect(url_for('dashboard'))

@app.route('/approve_job/<int:task_id>', methods=['POST'])
def approve_job(task_id):
    user = get_current_user()
    rating = request.form.get('rating')
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ? AND client_id = ?', (task_id, user['id'])).fetchone()
        if task and task['status'] == 'SUBMITTED':
            # Pay Helper
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (task['bounty'], task['freelancer_id']))
            conn.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "CREDIT", ?, ?)',
                         (task['freelancer_id'], task['bounty'], f"Earnings: {task['title']}"))

            # Update Rating
            if rating:
                conn.execute('UPDATE users SET rating_sum = rating_sum + ?, rating_count = rating_count + 1 WHERE id = ?',
                             (float(rating), task['freelancer_id']))
                conn.execute('UPDATE tasks SET rating = ? WHERE id = ?', (rating, task_id))

            conn.execute('UPDATE tasks SET status = "COMPLETED" WHERE id = ?', (task_id,))
            conn.commit()
            flash("Payment released! Project closed.")
    return redirect(url_for('dashboard'))

@app.route('/cancel_job/<int:task_id>', methods=['POST'])
def cancel_job(task_id):
    user = get_current_user()
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ? AND client_id = ? AND status = "OPEN"', (task_id, user['id'])).fetchone()
        if task:
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (task['bounty'], user['id']))
            conn.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "CREDIT", ?, ?)',
                         (user['id'], task['bounty'], f"Refund: Withdrawn {task['title']}"))
            conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            flash("Project withdrawn. Wallet refunded.")
    return redirect(url_for('dashboard'))

@app.route('/admin_fail/<int:task_id>', methods=['POST'])
def admin_fail(task_id):
    user = get_current_user()
    if not user or user['role'] != 'ADMIN':
        flash("Unauthorized access.")
        return redirect(url_for('dashboard'))
    with get_db() as conn:
        task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task:
            if task['freelancer_id']:
                # Penalty for helper
                conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (task['bounty'], task['freelancer_id']))
                conn.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "DEBIT", ?, ?)',
                             (task['freelancer_id'], task['bounty'], f"Penalty: Failed project {task['title']}"))

            # Refund owner
            conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (task['bounty'], task['client_id']))
            conn.execute('INSERT INTO transactions (user_id, type, amount, description) VALUES (?, "CREDIT", ?, ?)',
                         (task['client_id'], task['bounty'], f"Admin Refund: {task['title']} due to failure"))

            conn.execute('UPDATE tasks SET status = "FAILED" WHERE id = ?', (task_id,))
            conn.commit()
            flash("Admin Action: Project Terminated. Funds returned to owner.")
    return redirect(url_for('admin_panel'))

@app.route('/admin')
def admin_panel():
    user = get_current_user()
    if not user or user['role'] != 'ADMIN':
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        # Get all users
        users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
        # Get all tasks with client/freelancer names
        tasks = conn.execute('''
            SELECT t.*, u_c.name as client_name, u_f.name as freelancer_name
            FROM tasks t
            JOIN users u_c ON t.client_id = u_c.id
            LEFT JOIN users u_f ON t.freelancer_id = u_f.id
            ORDER BY t.id DESC
        ''').fetchall()
        # Stats
        total_users = len(users)
        total_tasks = len(tasks)
        active_tasks = conn.execute('SELECT COUNT(*) FROM tasks WHERE status IN ("OPEN", "ASSIGNED", "SUBMITTED")').fetchone()[0]
        total_transactions = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]

    ADMIN_TEMPLATE = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>ASSIGNMATE - Admin Panel</title>
        <style>{{ css }}</style>
    </head>
    <body>
        {{ nav_partial | safe }}
        <div class="main">
            <div class="animate-fadeIn">
                <div style="margin-bottom: 3.5rem;">
                    <h1 style="font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em;">🛡️ Admin Control Center</h1>
                    <p style="color: var(--text-muted); font-size: 1.1rem; margin-top: 0.4rem; font-weight: 500;">Manage users, tasks, and platform operations</p>
                </div>

                {% with messages = get_flashed_messages() %}
                    {% if messages %}{% for m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}
                {% endwith %}

                <!-- Admin Stats -->
                <div class="stats-grid" style="grid-template-columns: repeat(4, 1fr);">
                    <div class="stat-card">
                        <div class="stat-label">Total Users</div>
                        <div class="stat-value">{{ total_users }}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Tasks</div>
                        <div class="stat-value">{{ total_tasks }}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Active Tasks</div>
                        <div class="stat-value" style="color: #F59E0B;">{{ active_tasks }}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Transactions</div>
                        <div class="stat-value">{{ total_transactions }}</div>
                    </div>
                </div>

                <!-- Users Management -->
                <div class="card" style="margin-bottom: 2rem;">
                    <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem;">👥 User Management</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>USN</th>
                                <th>Name</th>
                                <th>Role</th>
                                <th>Balance</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for u in users %}
                            <tr>
                                <td style="font-weight: 700;">#{{ u.id }}</td>
                                <td>{{ u.usn }}</td>
                                <td style="font-weight: 700;">{{ u.name }}</td>
                                <td><span class="badge" style="background: {% if u.role == 'ADMIN' %}#EF4444{% elif u.role == 'TUTOR' %}#10B981{% else %}#3B82F6{% endif %}; color: white;">{{ u.role }}</span></td>
                                <td style="font-family: 'Outfit'; font-weight: 700;">₹{{ "%.2f"|format(u.balance) }}</td>
                                <td><span class="badge" style="background: {% if u.is_verified %}#D1FAE5{% else %}#FEF3C7{% endif %}; color: {% if u.is_verified %}#065F46{% else %}#B45309{% endif %};">{{ 'VERIFIED' if u.is_verified else 'PENDING' }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                <!-- All Tasks -->
                <div class="card">
                    <h2 style="font-size: 1.5rem; font-weight: 800; margin-bottom: 1.5rem;">📋 All Tasks</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Title</th>
                                <th>Client</th>
                                <th>Helper</th>
                                <th>Bounty</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for task in tasks %}
                            <tr>
                                <td style="font-weight: 700;">#{{ task.id }}</td>
                                <td style="font-weight: 700;">{{ task.title[:30] }}{% if task.title|length > 30 %}...{% endif %}</td>
                                <td>{{ task.client_name }}</td>
                                <td>{{ task.freelancer_name or '-' }}</td>
                                <td style="font-family: 'Outfit'; font-weight: 700; color: var(--primary);">₹{{ task.bounty }}</td>
                                <td><span class="badge badge-{{ task.status }}">{{ task.status }}</span></td>
                                <td>
                                    {% if task.status not in ['COMPLETED', 'FAILED'] %}
                                    <form action="{{ url_for('admin_fail', task_id=task.id) }}" method="POST" style="display: inline;">
                                        <button type="submit" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: var(--danger);">Force Fail</button>
                                    </form>
                                    {% else %}
                                    <span style="color: var(--text-muted); font-size: 0.8rem;">Closed</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(ADMIN_TEMPLATE, user=user, users=users, tasks=tasks,
                                  total_users=total_users, total_tasks=total_tasks,
                                  active_tasks=active_tasks, total_transactions=total_transactions,
                                  active_page='admin', css=BASE_CSS, nav_partial=render_nav(user, 'admin'))

if __name__ == '__main__':
    # Force DB init and seed dummy data
    init_db()
    seed_dummy_data()  # Clear and repopulate with dummy data
    app.run(debug=True)
