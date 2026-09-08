import os
from pathlib import Path
from uuid import uuid4
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from stock_god.adapters.data import PROVIDER
from stock_god.db.session import ROOT


def publish_teaching_snapshot():
    directory = ROOT / "data" / "market"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (PROVIDER.version + ".parquet")
    if not target.exists():
        rows = [{"symbol": symbol, **bar, "source": "teaching", "version": PROVIDER.version} for symbol, bars in PROVIDER.data.items() for bar in bars]
        tmp = directory / (str(uuid4()) + ".parquet.tmp")
        pq.write_table(pa.Table.from_pylist(rows), tmp)
        os.replace(tmp, target)
    with duckdb.connect() as connection:
        count = connection.execute("SELECT count(*) FROM read_parquet(?)", [str(target)]).fetchone()[0]
        if count != (PROVIDER.last_day + 1) * len(PROVIDER.names):
            raise ValueError("教学行情快照行数校验失败。")
    return target

