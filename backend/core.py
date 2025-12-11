import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@db:5432/code_analysis')

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initialize the database. Gracefully skip if DB is unavailable (for local dev)."""
    try:
        import asyncpg
        # Look for init SQL at both possible paths
        sql_path = os.path.exists('/app/infra/init_db.sql') and '/app/infra/init_db.sql' or \
                   os.path.exists('./infra/init_db.sql') and './infra/init_db.sql' or None
        
        if sql_path and os.path.exists(sql_path):
            with open(sql_path, 'r') as f:
                sql = f.read()
            # Extract DSN from DATABASE_URL (remove +asyncpg protocol)
            dsn = DATABASE_URL.replace('+asyncpg', '')
            conn = await asyncpg.connect(dsn=dsn)
            await conn.execute(sql)
            await conn.close()
            print('Database initialized successfully')
    except Exception as e:
        # Log warning but don't fail startup — allows local dev without a live DB
        print(f'[WARNING] Database initialization skipped: {e}')
