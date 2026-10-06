from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite connection with thread safety check disabled for FastAPI dependency injection
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from sqlalchemy import inspect, text

def init_db():
    """Create tables and apply incremental SQLite migrations for new schema columns."""
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    
    # 1. Check meeting_summaries
    if "meeting_summaries" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("meeting_summaries")]
        with engine.begin() as conn:
            if "discussion_topics" not in columns:
                conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN discussion_topics JSON DEFAULT '[]'"))
            if "minutes_of_meeting" not in columns:
                conn.execute(text("ALTER TABLE meeting_summaries ADD COLUMN minutes_of_meeting JSON DEFAULT '{}'"))
                
    # 2. Check decisions
    if "decisions" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("decisions")]
        with engine.begin() as conn:
            if "made_by" not in columns:
                conn.execute(text("ALTER TABLE decisions ADD COLUMN made_by VARCHAR(128)"))

    # 3. Check action_items
    if "action_items" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("action_items")]
        with engine.begin() as conn:
            if "domain" not in columns:
                conn.execute(text("ALTER TABLE action_items ADD COLUMN domain VARCHAR(64) DEFAULT 'Other'"))
            if "status" not in columns:
                conn.execute(text("ALTER TABLE action_items ADD COLUMN status VARCHAR(32) DEFAULT 'Pending'"))

    # 4. Check unresolved_questions
    if "unresolved_questions" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("unresolved_questions")]
        with engine.begin() as conn:
            if "answer" not in columns:
                conn.execute(text("ALTER TABLE unresolved_questions ADD COLUMN answer TEXT"))
            if "status" not in columns:
                conn.execute(text("ALTER TABLE unresolved_questions ADD COLUMN status VARCHAR(32) DEFAULT 'Unanswered'"))


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

