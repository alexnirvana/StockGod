from threading import Event
from stock_god.adapters.vnpy_events import WorkerEvents, smoke_test


def test_vnpy_core_dispatches_without_gui_or_gateway():
    assert smoke_test()['headless_event_loop'] == 'passed'


def test_worker_dispatcher_contains_callback_failure():
    completed = Event()
    calls = []
    def handler():
        calls.append(1)
        completed.set()
        raise ValueError('test task failure')
    events = WorkerEvents(handler)
    events.start()
    try:
        events.notify()
        assert completed.wait(3)
    finally:
        events.stop()
    assert calls == [1]
