import sqlite3; c=sqlite3.connect('vault.db'); c.execute("UPDATE jobs SET status='PENDING', current_stage='SCRIPT' WHERE id=29"); c.commit(); c.close()
