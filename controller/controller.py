from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request, Response, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
import os
import uuid
import hmac
import logging
import traceback
from dotenv import load_dotenv

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from config.database import get_db, init_db
from config.security import APP_PASSWORD, create_jwt_token, verify_jwt_token
from config.limiter import limiter, LOGIN_RATE_LIMIT, AI_RATE_LIMIT, DEFAULT_RATE_LIMIT
from config.logger import get_logger
from entity.rachunek import Rachunek
from entity.elementy import Element
from service.ai import analyze_receipt
from models import LoginRequest, ItemCreate, ReceiptSaveRequest

load_dotenv()

logger = get_logger("zarzadzca.controller")


app = FastAPI(title="Zarządca Paragonów")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

init_db()

os.makedirs("static", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

router = APIRouter()

app.mount("/static", StaticFiles(directory="static"), name="static")


async def require_auth(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(status_code=401, detail="Wymagane zalogowanie hasłem!")

    try:
        payload = verify_jwt_token(token)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Sesja wygasła lub nieprawidłowa: {str(e)}")


@router.get("/")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def root(request: Request):
    return FileResponse("static/index.html")


@router.post("/login")
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, payload: LoginRequest, response: Response):
    if not hmac.compare_digest(payload.password, APP_PASSWORD):
        logger.warning("❌ Nieudana próba logowania – błędne hasło.")
        raise HTTPException(status_code=401, detail="Nieprawidłowe hasło dostępu!")

    token = create_jwt_token({"user": "home_user"})

    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/"
    )

    logger.info("✅ Zalogowano pomyślnie. Wygenerowano token JWT.")
    return {"status": "ok", "message": "Zalogowano pomyślnie"}


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, response: Response):
    response.delete_cookie("auth_token", path="/")
    response.delete_cookie("user_account", path="/")
    return {"status": "ok", "message": "Wylogowano"}


@router.get("/check-auth")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def check_auth(request: Request, auth=Depends(require_auth)):
    return {"authenticated": True, "user": auth.get("user")}


@router.get("/uploads/{filename}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def pobierz_zdjecie_paragonu(request: Request, filename: str, auth=Depends(require_auth)):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join("uploads", safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Plik zdjęcia nie istnieje")
    return FileResponse(file_path)


@router.post("/analizuj")
@limiter.limit(AI_RATE_LIMIT)
async def analizuj_paragon(request: Request, file: UploadFile = File(...), auth=Depends(require_auth)):
    try:
        logger.info(f"📥 /analizuj | Nazwa pliku: '{file.filename}'")
        contents = await file.read()

        if not contents or len(contents) == 0:
            raise ValueError("Przesłany plik jest pusty!")

        if len(contents) > 15 * 1024 * 1024:
            raise ValueError("Plik zdjęcia jest za duży (maksymalnie 15 MB)!")


        ext = os.path.splitext(file.filename)[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        saved_path = os.path.join("uploads", filename)

        with open(saved_path, "wb") as f:
            f.write(contents)

        receipt_data = analyze_receipt(contents)

        return {
            "picture_path": f"/uploads/{filename}",
            "store_name": receipt_data.store_name,
            "date": receipt_data.date,
            "total_amount": receipt_data.total_amount,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity or 1.0,
                    "unit_price": item.unit_price or item.total_price,
                    "total_price": item.total_price
                } for item in receipt_data.items
            ]
        }
    except Exception as e:
        logger.error(f"❌ Błąd w /analizuj: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Błąd analizy paragonu: {str(e)}")


@router.post("/dodaj")
@limiter.limit("30/minute")
async def dodaj_paragon(request: Request, payload: ReceiptSaveRequest, db: Session = Depends(get_db), auth=Depends(require_auth)):
    try:
        nowy_rachunek = Rachunek(
            store_name=payload.store_name,
            cost=payload.cost,
            purchase_date=payload.purchase_date,
            sender=payload.account,
            picture_path=payload.picture_path,
            elementy=[
                Element(
                    name=item.name,
                    cost=item.total_price,
                    quantity=item.quantity
                ) for item in payload.items
            ]
        )

        db.add(nowy_rachunek)
        db.commit()
        db.refresh(nowy_rachunek)

        return {
            "status": "ok",
            "id": nowy_rachunek.id,
            "saved_cost": nowy_rachunek.cost,
            "items_saved": len(nowy_rachunek.elementy)
        }
    except Exception as e:
        logger.error(f"❌ Błąd w /dodaj: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Błąd zapisu w bazie: {str(e)}")


@router.get("/dashboard-summary")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def pobierz_podsumowanie_dashboardu(request: Request, db: Session = Depends(get_db), auth=Depends(require_auth)):
    results = db.query(Rachunek.sender, func.sum(Rachunek.cost)).group_by(Rachunek.sender).all()

    totals = {"T": 0.0, "O": 0.0, "K": 0.0}
    for sender, sum_cost in results:
        if sender in totals and sum_cost:
            totals[sender] = float(sum_cost)

    grand_total = sum(totals.values())

    return {
        "totals": totals,
        "grand_total": grand_total
    }


@router.get("/historie")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def pobierz_historie(request: Request, account: Optional[str] = "ALL", db: Session = Depends(get_db), auth=Depends(require_auth)):
    query = db.query(Rachunek)
    if account and account != "ALL":
        query = query.filter(Rachunek.sender == account)

    rachunki = query.order_by(Rachunek.id.desc()).all()
    return [
        {
            "id": r.id,
            "store_name": r.store_name,
            "cost": r.cost,
            "purchase_date": r.purchase_date,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            "sender": r.sender,
            "items_count": len(r.elementy)
        } for r in rachunki
    ]


@router.get("/rachunek/{rachunek_id}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def pobierz_szczegoly_rachunku(request: Request, rachunek_id: int, db: Session = Depends(get_db), auth=Depends(require_auth)):
    rachunek = db.query(Rachunek).options(joinedload(Rachunek.elementy)).filter(Rachunek.id == rachunek_id).first()
    if not rachunek:
        raise HTTPException(status_code=404, detail="Nie znaleziono paragonu")

    return {
        "id": rachunek.id,
        "store_name": rachunek.store_name,
        "cost": rachunek.cost,
        "purchase_date": rachunek.purchase_date,
        "created_at": rachunek.created_at.strftime("%Y-%m-%d %H:%M") if rachunek.created_at else "",
        "sender": rachunek.sender,
        "picture_path": rachunek.picture_path,
        "items": [
            {
                "id": el.id,
                "name": el.name,
                "cost": el.cost,
                "quantity": el.quantity
            } for el in rachunek.elementy
        ]
    }

app.include_router(router)