from fastapi import FastAPI

from routers import connectors, reservations, sessions, payments, stations

app = FastAPI(title="VoltWise EV Charging API")

app.include_router(stations.router)
app.include_router(connectors.router)
app.include_router(reservations.router)
app.include_router(sessions.router)
app.include_router(payments.router)


@app.get("/")
async def root():
    return {"message": "VoltWise API is running successfully"}