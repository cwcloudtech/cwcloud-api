import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from exceptions.CwHTTPException import CwHTTPException
from utils.common import get_env_int
from utils.logger import log_msg

postgres_db_name = os.getenv("POSTGRES_DB")
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_port = get_env_int("POSTGRES_PORT", 5432)
postgres_host = os.getenv("POSTGRES_HOST")
postgres_pool_size = get_env_int("POSTGRES_SIZE_POOL", 30)
postgres_max_overflow = get_env_int("POSTGRES_MAX_OVERFLOW", 10)
postgres_pool_timeout = get_env_int("POSTGRES_POOL_TIMEOUT", 30)
postgres_pool_recycle = get_env_int("POSTGRES_POOL_RECYCLE", 1800)

POSTGRES_URL = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db_name}"

dbEngine = create_engine(
    POSTGRES_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=postgres_pool_size,
    max_overflow=postgres_max_overflow,
    pool_timeout=postgres_pool_timeout,
    pool_recycle=postgres_pool_recycle,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dbEngine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except CwHTTPException as cwe:
        log_msg("WARN", f"[get_db] unexpected CwHTTPException: e.msg = {cwe.message}, e.status_code = {cwe.status_code}")
        raise cwe
    except Exception as e:
        log_msg("ERROR", f"[get_db] unexpected error: e.type = {type(e).__name__}, e.file = {__file__}, e.lno = {e.__traceback__.tb_lineno}, e.msg={str(e)}")
        raise e
    finally:
        db.close()
