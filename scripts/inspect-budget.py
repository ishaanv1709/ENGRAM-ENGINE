"""Inspect queue timing without exposing credential-derived budget keys."""
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from psycopg.rows import dict_row
from collective.settings import settings

with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
    for label, query in [
        ("waiters", "SELECT split_part(key,':',1) AS model,left(md5(key),8) AS budget_group,created_at,last_seen FROM model_waiters ORDER BY created_at"),
        ("reservations", "SELECT split_part(key,':',1) AS model,left(md5(key),8) AS budget_group,tokens,created_at FROM model_reservations WHERE created_at>now()-interval '90 seconds' ORDER BY created_at"),
    ]:
        print(json.dumps({label: connection.execute(query).fetchall()}, default=str))
