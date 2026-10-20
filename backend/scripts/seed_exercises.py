"""运行：python backend/scripts/seed_exercises.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, initialize_database
from app.services.exercise_library import ensure_exercise_seed

initialize_database()
with SessionLocal() as db:
    added = ensure_exercise_seed(db)
    db.commit()
print(f"动作库完成：新增 {added} 个动作。")
