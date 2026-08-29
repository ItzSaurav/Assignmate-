# Assignmate

A peer-to-peer student tutoring platform prototype built with Flask and SQLite. Implements role-based authentication, gig task management, and an internal database-simulated escrow ledger.

> Built as an academic course project by Team DETONATORS V4 at GCEM (VTU).

## Project Overview

Assignmate was created as a course project exploring web development, relational database modeling, and user access control. The platform connects students seeking academic assistance with peer tutors.

## Key Features

- **Role-Based Access Control**: Separate permissions and views for Students, Tutors, and Administrators.
- **Task Postings**: Create, browse, bid on, and complete academic tutoring tasks.
- **Simulated Escrow Ledger**: Internal database ledger that reserves user balance upon task assignment and credits the tutor upon completion approval.
- **User Reputation**: Task rating and review storage within SQLite.

## Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, Jinja2 Templates
- **Authentication**: Werkzeug password hashing, session cookies

## Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ItzSaurav/Assignmate-.git
   cd Assignmate-
   ```

2. Install dependencies:
   ```bash
   pip install flask werkzeug
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Navigate to `http://localhost:5000` in your web browser.

## Academic Disclaimer

This project is an educational prototype developed for academic coursework. The escrow mechanism is a simulated database transaction model, not an integrated real-money financial gateway.

## License

MIT License.
