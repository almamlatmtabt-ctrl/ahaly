# Ahilya Web App

A Flask-based web application for a smart watch order flow with login, OTP, and personal information pages.

## Features

- Multi-page user flow
- Arabic and English pages
- SQLite-backed request tracking
- Admin dashboard access
- Docker-ready setup

## Requirements

- Python 3.12+
- pip

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The app will run on:

- http://127.0.0.1:5000

## Docker

```bash
docker build -t ahilya-app .
docker run -p 5000:5000 ahilya-app
```

## Environment

You can set the app port with:

```bash
PORT=5000
```

## Notes

The database is stored locally under the `instance/` folder and is ignored by Git to keep the repository clean.
