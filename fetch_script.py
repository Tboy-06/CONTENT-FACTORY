import sqlite3; c=sqlite3.connect('vault.db'); print(c.execute("SELECT metadata_json FROM assets WHERE job_id=29 AND asset_type='script' ORDER BY created_at DESC LIMIT 1").fetchone()[0])
