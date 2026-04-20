from flask import Blueprint

textbook_bp = Blueprint('textbook', __name__)

from src.textbook import routes  # noqa: E402, F401
