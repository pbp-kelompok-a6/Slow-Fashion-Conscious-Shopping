"""Real file-backed SQLite for concurrency tests; never touch db.sqlite3."""
import atexit
from pathlib import Path
from tempfile import TemporaryDirectory

from lapakaian.settings import *  # noqa: F403

_test_directory = TemporaryDirectory(prefix="lapakaian-phase4-")
atexit.register(_test_directory.cleanup)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(Path(_test_directory.name) / "unused.sqlite3"),
        "TEST": {"NAME": str(Path(_test_directory.name) / "concurrency.sqlite3")},
        "OPTIONS": {"timeout": 2},
    }
}
MEDIA_ROOT = str(Path(_test_directory.name) / "media")
