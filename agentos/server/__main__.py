"""Run API: ``python -m agentos.server`` (development server; production: use gunicorn)."""

from __future__ import annotations

from agentos.config import settings
from agentos.server.app import app


def main() -> None:
    app.run(
        host=settings.API_HOST,
        port=settings.API_PORT,
        threaded=True,
        debug=settings.FLASK_DEBUG,
        use_reloader=settings.FLASK_DEBUG,
    )


if __name__ == "__main__":
    main()
