# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Require teacher login to register or remove students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/teachers/login`                                                 | Sign in with a teacher account                                      |
| POST   | `/teachers/logout`                                                | Sign out the current teacher                                        |
| GET    | `/teachers/session`                                                | Check whether the current browser has a teacher session             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher login required)                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remove a student (teacher login required)                         |

Teacher accounts are read from `teachers.json` as a JSON object of usernames
and passwords. Assign unique passwords before deployment; the browser session
cookie is HTTP-only and expires after eight hours.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
