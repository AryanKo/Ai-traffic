"""Keep test imports of backend.main from touching the real data/trafficmind.db.

backend/main.py instantiates a module-level Store(DB_PATH) so uvicorn can load
"main:app" by string. Any test that does `from main import create_app` runs
that line too, which would otherwise create/open the real on-disk database as
a side effect of import and leave it permanently stuck on whatever schema
existed the first time a test ran (CREATE TABLE IF NOT EXISTS never migrates
an existing table). Point it at a throwaway temp file instead, before any
test module gets the chance to import main.
"""
import os
import tempfile

os.environ.setdefault("TRAFFIC_DB", os.path.join(tempfile.mkdtemp(), "test-main-import.db"))
