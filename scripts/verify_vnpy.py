"""Verify the bundled, unchanged official vn.py 4.2.0 event core."""
from stock_god.adapters.vnpy_events import smoke_test

if __name__ == "__main__":
    print(smoke_test())
