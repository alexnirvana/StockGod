"""vn.py event-core adapter. Never creates a gateway or writes the ledger."""
from threading import Event as ThreadEvent
import logging
from stock_god._vendor.vnpy_event import Event, EventEngine


def smoke_test():
    received = ThreadEvent()
    engine = EventEngine(interval=0.05)
    engine.register("stockgod.teaching", lambda event: received.set() if event.data == "teaching" else None)
    engine.start()
    try:
        engine.put(Event("stockgod.teaching", "teaching"))
        if not received.wait(timeout=3):
            raise RuntimeError("vn.py event loop did not dispatch the teaching event")
    finally:
        engine.stop()
    return {"adapter": "vnpy.event 4.2.0 (vendored core)", "headless_event_loop": "passed", "broker_gateway": "absent"}


class WorkerEvents:
    """Coalesced task notifications. The database remains the durable task source."""

    def __init__(self, handler):
        self.engine = EventEngine()
        self.pending = ThreadEvent()
        self.handler = handler
        self.engine.register("stockgod.jobs.poll", self._dispatch)

    def _dispatch(self, event):
        try:
            self.handler()
        except Exception:
            logging.getLogger("stock_god.worker").exception("Worker notification failed")
        finally:
            self.pending.clear()

    def start(self):
        self.engine.start()

    def notify(self):
        if not self.pending.is_set():
            self.pending.set()
            self.engine.put(Event("stockgod.jobs.poll"))

    def stop(self):
        self.engine.stop()


if __name__ == "__main__":
    print(smoke_test())
