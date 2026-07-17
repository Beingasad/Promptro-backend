import sqlite3

def check_all_prompts(db_path):
    print(f"=== Checking all prompts in: {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Tables in database:", [t[0] for t in tables])
        
        if ('prompts',) in tables or ('prompts' in [t[0] for t in tables]):
            cursor.execute("SELECT COUNT(*) FROM prompts")
            count = cursor.fetchone()[0]
            print(f"Total rows in 'prompts' table: {count}")
            
            cursor.execute("SELECT id, title, category, created_at FROM prompts ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for r in rows:
                print(f"ID: {r[0]} | Title: {r[1]} | Category: {r[2]} | Date: {r[3]}")
        conn.close()
    except Exception as e:
        print("Error:", e)

check_all_prompts("d:/Promptro_web/promptro.db")
