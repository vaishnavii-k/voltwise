import asyncio
from datetime import datetime, timedelta, timezone
from database import AsyncSessionLocal 
from models import Station, Connector, Slot

async def add_fake_data():
    print("Adding fake data to the database...")
    async with AsyncSessionLocal() as db:
        station = Station(name="Test Station", location="Downtown", total_capacity_kw=100.0)
        db.add(station)
        await db.commit()
        await db.refresh(station)

        connector = Connector(station_id=station.id, type="CSS", max_power_kw=50.0)
        db.add(connector)
        await db.commit()
        await db.refresh(connector)

        now = datetime.now(timezone.utc)
        slot = Slot(
            connector_id=connector.id,
            start_time=now + timedelta(days=1), 
            end_time=now + timedelta(days=1, hours=2), 
            status="available",
            price_per_kwh=15.0 
        )
        db.add(slot)
        await db.commit()
        print("Success! Data added.")

if __name__ == "__main__":
    asyncio.run(add_fake_data())