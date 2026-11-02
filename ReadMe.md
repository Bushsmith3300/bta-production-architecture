Bush Teaching Assistant (BTA) – Backend

A Python-Powered Educational Technology Platform

Project Overview

Bush Teaching Assistant (BTA) is an educational technology platform developed to support Ghanaian Senior High School (SHS) students in preparing for examinations through interactive quizzes, practice questions, performance tracking and digital learning resources.

The backend is built with Python and Flask and provides the application logic, database operations, authentication, API endpoints and administrative functionality.

BTA is a live application currently being used by students.

Key Features

1. User Authentication and Management

- Student registration and login.
- Secure password handling.
- Session-based authentication.
- Role-based access control.
- User account management.

2. Question Management

- Create, retrieve, update and delete examination questions.
- Organise questions by subject and topic.
- Support multiple-choice questions.
- Store correct answers and explanations.
- Categorise questions by difficulty level.
- Bulk question import and export.
- Search and filter question collections.

3. Online Assessment System

- Topic-based quizzes.
- Randomised question selection.
- Automatic answer evaluation.
- Immediate feedback and explanations.
- Student performance tracking.
- Quiz history management.

4. Administrative Management

- Student management.
- Subject management.
- Question administration.
- Announcement management.
- Online class management.
- Administrative dashboards.

5. Extra Classes Management

- Student and parent management.
- Teacher and subject management.
- Monthly fee management.
- Payment record management.
- Online payment integration.
- Payment status tracking.

6. Database Management

- Relational database architecture.
- SQLAlchemy ORM integration.
- Database migrations using Flask-Migrate and Alembic.
- Database relationships and integrity management.

Technologies Used

Technology| Purpose
Python| Backend programming language
Flask| Web application framework
PostgreSQL| Relational database
SQLAlchemy| Object-relational mapping
Flask-Migrate| Database migration management
Alembic| Database schema versioning
Flask-CORS| Cross-origin resource sharing
JavaScript| Frontend interactions
Paystack| Payment processing
Supabase| Managed PostgreSQL database hosting
Render| Application hosting
Git and GitHub| Version control

Application Architecture

The backend follows a modular Flask application architecture designed to improve maintainability, organisation and scalability.

The application separates its responsibilities into different components:

- Models: Database models and relationships.
- Routes: Application endpoints and business logic.
- Admin: Administrative functionality.
- Utils: Shared utility functions.
- Templates: Server-rendered HTML templates.
- Static: CSS, JavaScript and other static resources.
- Migrations: Database schema version history.

Database

PostgreSQL is used as the primary relational database management system.

SQLAlchemy provides the ORM layer for database interactions, while Flask-Migrate and Alembic manage database schema changes.

The database supports several application modules, including:

- User accounts.
- Subjects and examination questions.
- Student progress.
- Quiz history.
- Announcements.
- Live classes and assessments.
- Extra classes and enrolments.
- Monthly fees and payment records.

Payment Integration

The Extra Classes module integrates with Paystack to facilitate online fee payments.

The payment system supports transaction processing, payment status tracking and the management of payment records associated with students, parents, subjects and teachers.

Project Structure

The application is organised into modular components.

bta-production-architecture/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── admin/
│   ├── utils/
│   ├── templates/
│   └── static/
│
├── migrations/
├── populate_question_hashes.py
├── requirements.txt
├── run.py
└── README.md

Installation and Setup

Prerequisites

Before running the application, ensure you have:

- Python 3.10 or later.
- PostgreSQL.
- Git.
- pip.

1. Clone the Repository

git clone https://github.com/Bushsmith3300/bta-production-architecture.git

2. Navigate to the Project Directory

cd bta-production-architecture

3. Create a Virtual Environment

python -m venv venv

Activate the virtual environment.

Windows:

venv\Scripts\activate

Linux/macOS:

source venv/bin/activate

4. Install Dependencies

pip install -r requirements.txt

5. Configure Environment Variables

Configure the environment variables required by the application.

Example:

SECRET_KEY=your_secret_key
DATABASE_URL=your_database_connection_string

Additional environment variables may be required depending on the application configuration.

Never commit passwords, API keys or other sensitive credentials to GitHub.

6. Run Database Migrations

After configuring the database and Flask application:

flask db upgrade

7. Start the Application

python run.py

The application will start using the configured development server settings.

Deployment

The BTA application uses cloud infrastructure for hosting and database management.

- Backend Hosting: Render.
- Database Hosting: Supabase PostgreSQL.
- Payment Processing: Paystack.

The production environment is configured separately from local development.

Security

Security and data integrity are important considerations in the development of BTA.

The application incorporates authentication, role-based access control and secure database operations.

Production credentials and sensitive configuration values are managed through environment variables.

Sensitive student information, database passwords and payment gateway secret keys must never be exposed in public repositories.

Project Status

Status: Live and Actively Maintained

Bush Teaching Assistant is an ongoing software development project. The platform is currently being used by students, with continuous improvements and additional features being introduced.

Developer

Developer: Bushsmith3300

Professional Role: Python Software Developer

Education: BSc Petroleum Engineering

GitHub: https://github.com/Bushsmith3300

---

Building technology to make quality education and examination preparation more accessible to Ghanaian students.
