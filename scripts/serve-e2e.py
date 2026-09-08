"""An isolated browser-test API. Keeps all test records out of the player's DB."""
import os
import threading
import time
from pathlib import Path
from uuid import uuid4
import uvicorn
from stock_god.api.main import create_app
from stock_god.jobs.worker import run_once, heartbeat

database_path = Path(os.getenv("E2E_DATABASE", Path(__file__).resolve().parents[1] / "data" / ("e2e-" + str(uuid4()) + ".sqlite")))
app = create_app("sqlite:///" + database_path.as_posix())

def worker():
    time.sleep(3)
    while True:
        try:
            heartbeat(app.state.factory.kw['bind'])
            run_once(app.state.factory)
        except Exception:
            pass
        time.sleep(0.5)

threading.Thread(target=worker, daemon=True).start()
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
