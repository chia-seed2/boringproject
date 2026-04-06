from fastapi import APIRouter, Depends, HTTPException
from requests.exceptions import RequestException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.store import Store
from app.services.scan_persistence import save_scan_results
from app.services.site_scanner import ensure_scheme, scan_site

router = APIRouter()


@router.post("/scan-site")
def scan_site_endpoint(url: str, store_id: str | None = None, max_pages: int = 100, db: Session = Depends(get_db)):
    url = ensure_scheme(url)

    try:
        results = scan_site(url, max_pages=max_pages)

        if store_id:
            store = db.query(Store).filter(Store.id == store_id).first()
            if not store:
                raise HTTPException(status_code=404, detail="Store not found.")

            saved_results = save_scan_results(db, store_id, results)

            return {
                "url": url,
                "store_id": store_id,
                "found": len(results),
                "saved": len(saved_results),
                "results": saved_results
            }

        return {
            "url": url,
            "found": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except RequestException as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch website: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))