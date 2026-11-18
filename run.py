"""Development entry point. Production should use gunicorn run:app."""
from app import create_app

app = create_app()
