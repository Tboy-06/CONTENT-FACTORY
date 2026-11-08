import sqlite3; c=sqlite3.connect('vault.db'); c.execute("UPDATE approvals SET decision='APPROVED', resolved_at=CURRENT_TIMESTAMP WHERE job_id=29"); c.commit(); c.close()
