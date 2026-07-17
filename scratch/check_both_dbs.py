import sqlite3

def check_db(db_path):
    print(f"=== Checking database: {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print("Tables:", tables)
        if "prompts" in tables:
            cursor.execute("SELECT id, title, category, created_at, prompt_text FROM prompts ORDER BY created_at DESC LIMIT 10")
            rows = cursor.fetchall()
            for r in rows:
                print(f"ID: {r[0]} | Title: {r[1]} | Category: {r[2]} | Date: {r[3]}")
                print(f"Prompt: {r[4][:150]}...")
                print("-" * 20)
        conn.close()
    except Exception as e:
        print("Error:", e)

check_db("d:/Promptro_web/promptro.db")
check_db("d:/Promptro_web/backend/promptro.db")
