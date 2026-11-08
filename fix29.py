import sqlite3; c=sqlite3.connect('vault.db'); c.execute("UPDATE jobs SET status='PENDING' WHERE id=29"); c.commit(); c.close()
