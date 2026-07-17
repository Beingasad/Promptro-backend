import sqlite3

def check_db(db_path):
    print(f"=== Checking database: {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, prompt_text, category, image_url, created_at FROM prompts ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        for r in rows:
            print(f"ID: {r[0]}\nTitle: {r[1]}\nPrompt: {r[2]}\nCategory: {r[3]}\nImage: {r[4]}\nDate: {r[5]}\n")
        
        # Search specifically for Muharram keywords
        cursor.execute("SELECT id, title, prompt_text FROM prompts WHERE title LIKE '%muharram%' OR prompt_text LIKE '%muharram%' OR tags LIKE '%muharram%'")
        rows = cursor.fetchall()
        print("Search results:")
        for r in rows:
            print(f"ID: {r[0]}\nTitle: {r[1]}\nPrompt: {r[2]}\n")
        conn.close()
    except Exception as e:
        print("Error:", e)

check_db("d:/Promptro_web/promptro.db")
check_db("d:/Promptro_web/backend/promptro.db")
