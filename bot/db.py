import pathlib
import yoyo

DB_PATH = "/data/rankaisija.db"

_MIGRATIONS_DIR = str(pathlib.Path(__file__).parent.parent / "db" / "migrations")


def run_migrations():
    backend = yoyo.get_backend(f"sqlite:///{DB_PATH}")
    migrations = yoyo.read_migrations(_MIGRATIONS_DIR)
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))
