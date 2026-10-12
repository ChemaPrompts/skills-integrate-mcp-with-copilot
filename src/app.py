"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import os
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
ACTIVITIES_FILE = BASE_DIR / "activities.json"
TEACHERS_FILE = BASE_DIR / "teachers.json"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
    "GitHub Skills": {
        "description": "Learn practical coding and collaboration skills through the GitHub Skills program",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 4:30 PM",
        "max_participants": 18,
        "participants": [],
    },
}

def load_json_data(path, default_data):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return default_data


def load_activities():
    return load_json_data(ACTIVITIES_FILE, DEFAULT_ACTIVITIES)


def load_teachers():
    with TEACHERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if (
        not isinstance(data, dict)
        or not data
        or any(
            not isinstance(username, str)
            or not username.strip()
            or not isinstance(password, str)
            or not password
            for username, password in data.items()
        )
    ):
        raise ValueError(f"{TEACHERS_FILE} must contain a non-empty username/password object")
    return data


def normalize_activity_name(name: str) -> str:
    return name.strip().replace("+", " ")


async def extract_email(request: Request, fallback_email: str | None = None):
    email = request.query_params.get("email") or fallback_email
    if email is None:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise HTTPException(status_code=400, detail="Request body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        email = payload.get("email")
    return email.strip() if isinstance(email, str) else None


class TeacherCredentials(BaseModel):
    username: str
    password: str


TEACHER_SESSION_COOKIE = "teacher_session"
TEACHER_SESSION_MAX_AGE = 8 * 60 * 60
teacher_sessions: dict[str, tuple[str, float]] = {}


def _teacher_username(request: Request) -> str | None:
    token = request.cookies.get(TEACHER_SESSION_COOKIE)
    session = teacher_sessions.get(token) if token else None
    if session is None:
        return None
    username, expires_at = session
    if expires_at <= time.time():
        teacher_sessions.pop(token, None)
        return None
    return username


def _require_teacher(request: Request) -> None:
    if _teacher_username(request) is None:
        raise HTTPException(
            status_code=401,
            detail="Teacher login required",
            headers={"WWW-Authenticate": "Bearer"},
        )


app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

# Mount the static files directory
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# In-memory activity database
activities = load_activities()
teachers = load_teachers()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(
    category: str | None = None,
    sort: str = "name",
    search: str | None = None,
):
    results = dict(activities)

    if category:
        category_key = category.strip().lower()
        results = {
            name: record
            for name, record in results.items()
            if (record.get("category", "General") or "General").lower() == category_key
        }

    if search:
        query = search.strip().lower()
        if query:
            results = {
                name: record
                for name, record in results.items()
                if query in name.lower() or query in record.get("description", "").lower()
            }

    valid_sort_options = {
        "name": lambda item: item[0].lower(),
        "participants": lambda item: len(item[1].get("participants", [])),
        "schedule": lambda item: item[1].get("schedule", "").lower(),
    }

    if sort.lower() in valid_sort_options:
        results = dict(sorted(results.items(), key=valid_sort_options[sort.lower()], reverse=sort.lower() == "participants"))

    return results


@app.post("/teachers/login")
def login_teacher(credentials: TeacherCredentials, request: Request, response: Response):
    username = credentials.username.strip()
    teacher_password = teachers.get(username)
    if teacher_password is None or not secrets.compare_digest(
        credentials.password, teacher_password
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    teacher_sessions[token] = (username, time.time() + TEACHER_SESSION_MAX_AGE)
    response.set_cookie(
        key=TEACHER_SESSION_COOKIE,
        value=token,
        max_age=TEACHER_SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"username": username}


@app.get("/teachers/session")
def get_teacher_session(request: Request):
    username = _teacher_username(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/teachers/logout")
def logout_teacher(request: Request, response: Response):
    token = request.cookies.get(TEACHER_SESSION_COOKIE)
    if token:
        teacher_sessions.pop(token, None)
    response.delete_cookie(
        key=TEACHER_SESSION_COOKIE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(activity_name: str, request: Request, email: str | None = None):
    """Sign up a student for an activity."""
    _require_teacher(request)
    activity_name = normalize_activity_name(activity_name)
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email is None:
        email = await extract_email(request)

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")

    activity = activities[activity_name]
    participants = activity.setdefault("participants", [])

    if email in participants:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    if len(participants) >= int(activity.get("max_participants", 0)):
        raise HTTPException(status_code=400, detail="Activity is already full")

    participants.append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
async def unregister_from_activity(activity_name: str, request: Request, email: str | None = None):
    """Unregister a student from an activity."""
    _require_teacher(request)
    activity_name = normalize_activity_name(activity_name)
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    if email is None:
        email = await extract_email(request)

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")

    activity = activities[activity_name]
    participants = activity.setdefault("participants", [])

    if email not in participants:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    participants.remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
