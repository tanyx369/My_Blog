from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"  # engine_name:///path_to_db (dialect+driver://username:password@host:port/database)

# Connection to the database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # special arguement for sqlite
)

# A session is a transaction of data (when commit changes)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Function that provide session to our routes
def get_db():
    with SessionLocal() as db:
        yield db
