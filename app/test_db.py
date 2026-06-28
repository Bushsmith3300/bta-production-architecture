import psycopg2
import time

DATABASE_URL = "postgresql://postgres.lnkdftlarfdsszfpskmv:Bhbush3300%2F@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"

print("Before connect")

start = time.time()

conn = psycopg2.connect(
    DATABASE_URL
)

print("Connected in:", time.time() - start)

cur = conn.cursor()

cur.execute("SELECT 1")

print("Query successful")

conn.close()