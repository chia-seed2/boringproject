from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.store import Store
from app.services.site_scanner import scan_site, ensure_scheme
from app.services.scan_persistence import save_scan_results
from app.services.compliance_service import calculate_all_variants_compliance


def run_daily_scan():
    db: Session = SessionLocal()
    summary = {
        "stores_total": 0,
        "stores_scanned": 0,
        "stores_failed": 0,
        "products_saved": 0,
        "errors": [],
    }

    try:
        stores = db.query(Store).all()
        summary["stores_total"] = len(stores)

        for store in stores:
            try:
                store_url = ensure_scheme(store.domain)
                results = scan_site(store_url, max_pages=300)
                saved = save_scan_results(db, store.id, results)

                summary["stores_scanned"] += 1
                summary["products_saved"] += len(saved)

            except Exception as e:
                summary["stores_failed"] += 1
                summary["errors"].append({
                    "store_id": store.id,
                    "store_name": store.name,
                    "domain": store.domain,
                    "error": str(e),
                })
                continue

        calculate_all_variants_compliance(db)
        return summary

    finally:
        db.close()