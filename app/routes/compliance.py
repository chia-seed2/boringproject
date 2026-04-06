from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.variant import Variant
from app.models.compliance_result import ComplianceResult
from app.services.compliance_service import (
    calculate_variant_compliance,
    calculate_all_variants_compliance,
)

router = APIRouter()


@router.post("/compliance/run/{variant_id}")
def run_variant_compliance(variant_id: str, db: Session = Depends(get_db)):
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")

    result = calculate_variant_compliance(db, variant_id)
    return result


@router.post("/compliance/run-all")
def run_all_compliance(db: Session = Depends(get_db)):
    results = calculate_all_variants_compliance(db)
    return {
        "processed": len(results),
        "results": results
    }


@router.get("/compliance-results")
def list_compliance_results(db: Session = Depends(get_db)):
    return (
        db.query(ComplianceResult)
        .order_by(ComplianceResult.checked_at.desc())
        .all()
    )