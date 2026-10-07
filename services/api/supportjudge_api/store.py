import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class Store:
    def __init__(self, path=None):
        self.path = str(path or os.environ.get("SUPPORTJUDGE_DB", "work/supportjudge.db"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, state TEXT, request TEXT, report TEXT, error TEXT, created TEXT);
                CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS annotations(id TEXT PRIMARY KEY, run_id TEXT, value TEXT, created TEXT);
                CREATE TABLE IF NOT EXISTS promotions(id TEXT PRIMARY KEY, run_id TEXT, settings_hash TEXT, created TEXT);
            """)

    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        return db

    def get(self, key):
        with self.connection() as db:
            row = db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO cache VALUES (?,?)", (key, json.dumps(value)))

    def create_run(self, request):
        run_id = uuid.uuid4().hex
        with self.connection() as db:
            active = db.execute("SELECT count(*) FROM runs WHERE state IN ('pending','running')").fetchone()[0]
            if active >= 10:
                raise ValueError("Run queue is full; wait for current jobs")
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)", (run_id, "pending", json.dumps(request), None, None, datetime.now(timezone.utc).isoformat()))
        return run_id

    def claim(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM runs WHERE state='pending' ORDER BY created LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE runs SET state='running' WHERE id=?", (row["id"],))
                return dict(row)
        return None

    def finish(self, run_id, report=None, error=None):
        with self.connection() as db:
            db.execute("UPDATE runs SET state=?,report=?,error=? WHERE id=?", ("failed" if error else "completed", json.dumps(report) if report else None, error, run_id))

    def interrupt(self):
        with self.connection() as db:
            db.execute("UPDATE runs SET state='failed',error='Worker interrupted; submit a new run. Completed calls remain cached.' WHERE state='running'")

    def runs(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT id,state,created,error FROM runs ORDER BY created DESC LIMIT 100")]

    def run(self, run_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["request"] = json.loads(result["request"])
        result["report"] = json.loads(result["report"]) if result["report"] else None
        return result

    def annotate(self, run_id, annotation):
        with self.connection() as db:
            db.execute("INSERT INTO annotations VALUES (?,?,?,?)", (uuid.uuid4().hex, run_id, json.dumps(annotation), datetime.now(timezone.utc).isoformat()))

    def annotations(self, run_id):
        with self.connection() as db:
            return [{**dict(row), "value": json.loads(row["value"])} for row in db.execute("SELECT * FROM annotations WHERE run_id=? ORDER BY created", (run_id,))]

    def promote(self, run_id, settings_hash):
        with self.connection() as db:
            db.execute("INSERT INTO promotions VALUES (?,?,?,?)", (uuid.uuid4().hex, run_id, settings_hash, datetime.now(timezone.utc).isoformat()))

    def promotions(self):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM promotions ORDER BY created DESC")]
