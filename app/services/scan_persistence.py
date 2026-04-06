from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.variant import Variant
from app.models.price_snapshot import PriceSnapshot


def to_decimal(value):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def save_scan_results(db: Session, store_id: str, results: list[dict]):
    saved = []

    for item in results:
        url = item.get("url")
        title = item.get("title") or "Untitled Product"
        price = to_decimal(item.get("price"))
        compare_at_price = to_decimal(item.get("compare_at_price"))
        currency = item.get("currency") or "EUR"
        sku = item.get("sku")

        if not url:
            continue

        product = db.query(Product).filter(Product.url == url).first()

        if not product:
            product = Product(
                store_id=store_id,
                external_id=url,
                title=title,
                handle=None,
                url=url,
                active=True,
            )
            db.add(product)
            db.commit()
            db.refresh(product)
        else:
            product.title = title
            db.commit()
            db.refresh(product)

        variant = db.query(Variant).filter(Variant.product_id == product.id).first()

        if not variant:
            variant = Variant(
                product_id=product.id,
                external_id=f"{product.id}-default",
                sku=sku,
                title="Default"
            )
            db.add(variant)
            db.commit()
            db.refresh(variant)
        else:
            variant.sku = sku
            db.commit()
            db.refresh(variant)

        snapshot = None
        if price is not None:
            snapshot = PriceSnapshot(
                variant_id=variant.id,
                price=price,
                compare_at_price=compare_at_price,
                currency=currency
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)

        saved.append({
            "product_id": product.id,
            "variant_id": variant.id,
            "snapshot_id": snapshot.id if snapshot else None,
            "url": url,
            "title": title,
            "price": str(price) if price is not None else None,
            "compare_at_price": str(compare_at_price) if compare_at_price is not None else None,
            "currency": currency,
            "sku": sku,
        })

    return saved