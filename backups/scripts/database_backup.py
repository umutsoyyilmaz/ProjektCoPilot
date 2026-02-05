import sqlite3

def init_db():
    conn = sqlite3.connect('project_copilot.db')
    cursor = conn.cursor()
    
    # 1. Gereksinimler Tablosu (Requirements)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,          -- Örn: FS_MM_041
            title TEXT NOT NULL,         -- Örn: PO Approval Workflow
            module TEXT,                 -- Örn: MM, SD, FI
            complexity TEXT,             -- Low, Medium, High
            status TEXT DEFAULT 'Draft', -- Draft, Ready, In Progress
            ai_status TEXT DEFAULT 'None', -- None, Draft, Full
            summary TEXT,                -- AI tarafından üretilen özet
            tech_spec TEXT,              -- AI tarafından üretilen teknik detay
            effort_days INTEGER          -- Tahmini efor
        )
    ''')
    
    # Örnek veri ekleyelim (Eğer tablo boşsa)
    cursor.execute("SELECT COUNT(*) FROM requirements")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO requirements (code, title, module, complexity, status, ai_status, effort_days)
            VALUES ('FS_MM_041', 'Purchase Order Approval Workflow', 'MM', 'Medium', 'In Progress', 'Draft', 8)
        ''')
        cursor.execute('''
            INSERT INTO requirements (code, title, module, complexity, status, ai_status, effort_days)
            VALUES ('FS_SD_012', 'Sales Order Output Management', 'SD', 'Low', 'Ready', 'Full', 3)
        ''')
    
    conn.commit()
    conn.close()
    print("Veritabanı başarıyla kuruldu ve örnek veriler eklendi!")

if __name__ == '__main__':
    init_db()
