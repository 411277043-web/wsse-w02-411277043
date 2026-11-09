# 資料庫設定（Database Configuration）：SQLite 連線，以及每次 Request 使用的 Session。
# 資料庫檔 unitprice.db 建立在專案根目錄；已列入 .gitignore，不提交到 GitHub。

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./unitprice.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db
