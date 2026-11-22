from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Connector, Station, Reservation, Tariff


def score_connector(
    connector,
    station,
    price,
    urgent,
    max_price
):
    score = 0.0

    # Prefer higher charging power
    score += min(30, float(connector.max_power_kw) / 4)

    # Prefer lower prices
    score += max(0, 30 - float(price))

    # Prefer CCS if no connector type preference is supplied
    if connector.connector_type.lower() == "ccs":
        score += 10

    # Apply urgency preference
    if urgent:
        score += 10

    # Penalize prices above user's budget
    if max_price is not None and float(price) > max_price:
        score -= 50

    return round(score, 2)


async def get_recommendations(
    db: AsyncSession,
    preferred_type: str | None,
    urgent: bool,
    max_price: float | None,
    limit: int = 5
):
    now = datetime.now(timezone.utc)

    # Get available connectors with their stations
    stmt = (
        select(Connector, Station)
        .join(Station, Connector.station_id == Station.id)
        .where(Connector.status == "available")
    )

    if preferred_type:
        stmt = stmt.where(
            Connector.connector_type.ilike(preferred_type)
        )

    result = await db.execute(stmt)
    connectors = result.all()

    recommendations = []

    for connector, station in connectors:

        # Find the current tariff for this station
        tariff_stmt = (
            select(Tariff)
            .where(
                and_(
                    Tariff.station_id == station.id,
                    Tariff.valid_from <= now,
                    or_(
                        Tariff.valid_until.is_(None),
                        Tariff.valid_until > now
                    )
                )
            )
            .order_by(Tariff.valid_from.desc())
        )

        tariff_result = await db.execute(tariff_stmt)
        tariff = tariff_result.scalars().first()

        if not tariff:
            continue

        price = float(tariff.price_per_kwh)

        # Check whether the connector has an active
        # or upcoming reservation
        reservation_stmt = select(Reservation).where(
            and_(
                Reservation.connector_id == connector.id,
                Reservation.start_time < datetime.max.replace(
                    tzinfo=timezone.utc
                ),
                Reservation.end_time > now,
                Reservation.status != "cancelled"
            )
        )

        reservation_result = await db.execute(reservation_stmt)
        existing_reservations = reservation_result.scalars().all()

        # Calculate score
        score = score_connector(
            connector,
            station,
            price,
            urgent,
            max_price
        )

        recommendations.append({
            "connector_id": connector.id,
            "station_name": station.station_name,
            "connector_type": connector.connector_type,
            "max_power_kw": float(connector.max_power_kw),
            "price_per_kwh": price,
            "is_reserved": len(existing_reservations) > 0,
            "score": score
        })

    # Sort by highest score
    recommendations.sort(
        key=lambda x: (x["is_reserved"], -x["score"])
    )

    return recommendations[:limit]