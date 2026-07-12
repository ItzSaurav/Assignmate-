# 📚 Assignmate

> **The Peer-to-Peer Student Tutoring Marketplace.**

Assignmate is a platform designed to connect students with verified peer tutors for academic help. Built with trust in mind, it features an escrow payment system to ensure fair compensation and quality work.

This project strongly aligns with **SDG 4 (Quality Education)** by promoting inclusive and equitable learning opportunities for students helping students.

*Built by Team DETONATORS V4.*

## 🚀 What It Does

Assignmate provides a complete workflow for academic gig work:
- **Clients (Students)** can post tasks, set a bounty, and hire freelancers.
- **Freelancers (Tutors)** can browse tasks, complete assignments, and earn money.
- **The Escrow System** securely holds the bounty until both parties are satisfied.

### 🌟 Features
- **Role-Based Authentication:** Secure USN-based login for Clients, Freelancers, and Admins.
- **Task & Bounty Management:** Full CRUD operations for academic gigs.
- **Escrow Wallet:** Built-in financial system to handle transactions safely.
- **Reputation System:** Five-star rating engine to build trust across the marketplace.
- **Admin Dashboard:** Centralized control for user verification and platform moderation.

## 🛠 Tech Stack

Assignmate is a monolithic web application built on a rock-solid Python stack:
- **Backend:** Python, Flask, Werkzeug
- **Database:** SQLite (with custom row factories for seamless data access)
- **Frontend Templates:** HTML, CSS, Jinja2

## 💻 Getting Started Locally

1. **Clone the repo:**
   ```bash
   git clone https://github.com/ItzSaurav/Assignmate-.git
   cd Assignmate-
   ```

2. **Install the dependencies:**
   ```bash
   pip install flask werkzeug
   ```

3. **Start the server:**
   ```bash
   python app.py
   ```
   *The database will auto-initialize on the first run. Check out the terminal output for the local port (usually `http://127.0.0.1:5000`).*

---
*Built by [Saurav](https://github.com/ItzSaurav) and Team DETONATORS V4.*