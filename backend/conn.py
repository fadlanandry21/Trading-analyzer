from db import get_conn

conn = get_conn()

if conn:
    print(f"status: Connect")
    conn.close()
else:
    print("status: Failed to Connect")