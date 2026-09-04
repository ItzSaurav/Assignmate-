# Assignmate

A peer-to-peer student tutoring and academic task marketplace built with Flask and SQLite, featuring USN-based role authentication and an escrow wallet system.

---

## Why We Built This

In college, students often need help with specific assignments, coding labs, or concept explanations, while other senior or peer students have the skills to assist. Assignmate provides a structured campus marketplace where students can post task bounties, review submissions, and compensate helpers safely.

---

## Core Features

- **Role-Based Authentication**: USN-based (University Seat Number) login supporting three distinct roles: Student Clients, Peer Tutors (Freelancers), and Platform Administrators.
- **Escrow Wallet System**: When a student posts a task, the bounty is temporarily locked in escrow from their wallet balance. Funds are released to the tutor only after the student approves the completed submission.
- **Task Lifecycle**: Full lifecycle tracking from Open -> In Progress -> Submitted -> Completed / Disputed.
- **Peer Reputation Engine**: Star ratings and review counts calculated automatically upon task completion to establish community credibility.
- **Admin Verification Panel**: Administrative dashboard to review user verifications, resolve disputed tasks, and maintain platform integrity.

---

## Tech Stack

- **Backend**: Python 3, Flask, Werkzeug security (password hashing)
- **Database**: SQLite3 (automatic schema initialization, row factories)
- **Frontend**: HTML5, CSS3, Jinja2 template rendering

---

## Project Structure

```text
Assignmate-/
├── app.py            # Complete Flask monolithic application (routes, models, templates)
├── assignmate.db     # SQLite database (auto-created on first run)
└── README.md         # Project documentation
```

---

## Running Locally

### 1. Clone the Repository
```bash
git clone https://github.com/ItzSaurav/Assignmate-.git
cd Assignmate-
```

### 2. Install Dependencies
```bash
pip install flask werkzeug
```

### 3. Start the Application
```bash
python app.py
```
The database schema will automatically initialize on first launch, and the server will start at `http://127.0.0.1:5000`.

---

## Academic Disclaimer

This project is an educational prototype developed for academic coursework at GCEM (VTU). The escrow mechanism is a simulated database transaction model, not an integrated real-money financial gateway.

---

## License

MIT License. Developed by Saurav Mishra and Team DETONATORS V4 for academic demonstration and learning.
