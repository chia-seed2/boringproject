from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.variant import Variant
from app.models.price_snapshot import PriceSnapshot
from app.models.compliance_result import ComplianceResult


def calculate_variant_compliance(db: Session, variant_id: str):
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    snapshots = (
        db.query(PriceSnapshot)
        .filter(
            PriceSnapshot.variant_id == variant_id,
            PriceSnapshot.captured_at >= thirty_days_ago
        )
        .order_by(PriceSnapshot.captured_at.desc())
        .all()
    )

    if not snapshots:
        result = ComplianceResult(
            variant_id=variant_id,
            lowest_30_day_price=None,
            current_price=None,
            compare_at_price=None,
            status="insufficient_data"
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result

    current = snapshots[0]
    lowest_price = min(snapshot.price for snapshot in snapshots if snapshot.price is not None)

    if current.compare_at_price is None:
        status = "no_discount"
    elif current.compare_at_price == lowest_price:
        status = "compliant"
    else:
        status = "violation"

    result = ComplianceResult(
        variant_id=variant_id,
        lowest_30_day_price=lowest_price,
        current_price=current.price,
        compare_at_price=current.compare_at_price,
        status=status
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return result


def calculate_all_variants_compliance(db: Session):
    variants = db.query(Variant).all()
    results = []

    for variant in variants:
        result = calculate_variant_compliance(db, variant.id)
        results.append(result)

    return results