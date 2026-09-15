"""Ein begrenzter Worker ohne Netzadapter oder frei ausführbare Ausdrücke."""

import json
import logging
import os
import time
from uuid import UUID

from platform_app.data.service import process_one

logger = logging.getLogger("platform.data.worker")


def main() -> None:
    organizations = tuple(
        UUID(value.strip())
        for value in os.environ.get("DATA_WORKER_ORGANIZATION_IDS", "").split(",")
        if value.strip()
    )
    if not organizations:
        raise RuntimeError("Der Datenworker benötigt explizit konfigurierte Organisationen.")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    while True:
        processed = False
        for organization in organizations:
            try:
                processed = process_one(organization) or processed
            except Exception as error:
                # Keine DB-Parameter, Zellwerte oder Originalexceptions protokollieren.
                logger.error(
                    json.dumps({"event": "data_worker_retry", "error_type": type(error).__name__})
                )
                time.sleep(2)
        if not processed:
            time.sleep(1)


if __name__ == "__main__":
    main()
