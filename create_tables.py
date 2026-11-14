import asyncio
from database import engine, Base
import models 

async def create_tables():
    print("Connecting to database to create tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Success! Tables created.")

if __name__ == "__main__":
    asyncio.run(create_tables())