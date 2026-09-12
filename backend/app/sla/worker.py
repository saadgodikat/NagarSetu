import time

from app.config import settings
from app.db import SessionLocal
from app.sla.service import run_sla_evaluation


def main() -> None:
    if not settings.default_sla_enabled:
        raise SystemExit("Set DEFAULT_SLA_ENABLED=true before starting the SLA worker")
    while True:
        db = SessionLocal()
        try:
            run_sla_evaluation(db)
        finally:
            db.close()
        time.sleep(settings.sla_poll_interval_seconds)


if __name__ == "__main__":
    main()
