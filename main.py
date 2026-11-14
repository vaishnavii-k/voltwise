from fastapi import FastAPI
from routers import slots, reservations, sessions, invoices

app = FastAPI(title="EV Charging API")

app.include_router(slots.router)
app.include_router(reservations.router)
app.include_router(sessions.router)
app.include_router(invoices.router)