# Initialize the queue representation
import sqlite3
import threading


class UploadsDB:
    def __init__(self, db_file: str):
        self.db_file = db_file
        with threading.Lock():
            self.db = sqlite3.connect(self.db_file)
            self.db.executescript("""
                  BEGIN TRANSACTION;
                  CREATE TABLE IF NOT EXISTS "uploads" (
                      "upload_id" TEXT NOT NULL,
                      "part_index" INTEGER NOT NULL
                  );
                  CREATE INDEX IF NOT EXISTS "pair_index" ON "uploads" (
                      "upload_id" ASC,
                      "part_index" ASC
                  );
    
                  COMMIT;
                  """)

    def put_upload_info(self, upload_id: str, part_index: int) -> int:
        """Puts information about finished upload and return total count of uploads for this upload_id"""
        with threading.Lock():
            self.db.execute("INSERT INTO uploads (upload_id, part_index) VALUES (?, ?)", (upload_id, part_index))
            self.db.commit()
            return self.get_upload_part_count(upload_id)

    def get_upload_part_count(self, upload_id: str) -> int:
        cur = self.db.execute("SELECT COUNT(*) FROM uploads WHERE upload_id=?", (upload_id,))
        return cur.fetchone()[0]

    def delete_upload_info(self, upload_id: str):
        with threading.Lock():
            self.db.execute("DELETE FROM uploads WHERE upload_id=?", (upload_id,))
            self.db.commit()

    def __del__(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
