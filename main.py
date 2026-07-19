from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import date, datetime
from supabase import create_client, Client
import os
import bcrypt
import base64

import models, schemas
from database import engine, get_db

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://abdjopeevusxxtzqffdf.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiZGpvcGVldnVzeHh0enFmZmRmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ0Mjc0MzcsImV4cCI6MjEwMDAwMzQzN30._IMelsEdtQq9wCWHJhLDKc6AAQLAb7JYgR8LOkmsdQ0")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        decoded = base64.b64decode(token).decode()
        username, role = decoded.split(":")
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid")
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    if user.role != role:
        raise HTTPException(status_code=401, detail="Role tidak sesuai")
    return user

app = FastAPI(title="Sistem Manajemen Setoran Sales API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://grosirin.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def upload_to_supabase(file: UploadFile, setoran_id: int) -> str:
    filename = f"{setoran_id}_{file.filename}"
    contents = await file.read()
    supabase.storage.from_("bukti-struk").upload(filename, contents, {"content-type": file.content_type})
    return f"{SUPABASE_URL}/storage/v1/object/public/bukti-struk/{filename}"


# --- ENDPOINT FOR SALES ---

@app.post("/sales/", response_model=schemas.SalesResponse, status_code=status.HTTP_201_CREATED)
def create_sales(sales: schemas.SalesCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db_sales = models.Sales(**sales.model_dump())
    db_sales.sisa_bayar = sales.total_invoice
    db.add(db_sales)
    db.commit()
    db.refresh(db_sales)
    return db_sales

@app.get("/sales/", response_model=list[schemas.SalesResponse])
def get_all_sales(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Sales).all()

@app.get("/sales/{id_sales}", response_model=schemas.SalesResponse)
def get_sales(id_sales: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sales = db.query(models.Sales).filter(models.Sales.id_sales == id_sales).first()
    if not sales:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
    return sales

@app.put("/sales/{id_sales}", response_model=schemas.SalesResponse)
def update_sales(id_sales: int, sales: schemas.SalesCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db_sales = db.query(models.Sales).filter(models.Sales.id_sales == id_sales).first()
    if not db_sales:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
    
    sudah_dibayar = db_sales.total_invoice - db_sales.sisa_bayar
    
    db_sales.nama_sales = sales.nama_sales
    db_sales.no_telp = sales.no_telp
    db_sales.alamat = sales.alamat
    db_sales.jadwal_bayar = sales.jadwal_bayar
    db_sales.total_invoice = sales.total_invoice
    db_sales.periode_minggu = sales.periode_minggu
    db_sales.sisa_bayar = max(0, sales.total_invoice - sudah_dibayar)
    
    db.commit()
    db.refresh(db_sales)
    return db_sales

@app.delete("/sales/{id_sales}")
def delete_sales(id_sales: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db_sales = db.query(models.Sales).filter(models.Sales.id_sales == id_sales).first()
    if not db_sales:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
    
    db.query(models.Setoran).filter(models.Setoran.id_sales == id_sales).delete()
    db.query(models.Sales).filter(models.Sales.id_sales == id_sales).delete()
    db.commit()
    return {"message": "Sales berhasil dihapus"}


# --- ENDPOINT FOR SETORAN ---

@app.post("/setoran/", response_model=schemas.SetoranResponse, status_code=status.HTTP_201_CREATED)
def create_setoran(setoran: schemas.SetoranCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    sales_exists = db.query(models.Sales).filter(models.Sales.id_sales == setoran.id_sales).first()
    if not sales_exists:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
        
    db_setoran = models.Setoran(**setoran.model_dump())
    db.add(db_setoran)
    db.commit()
    db.refresh(db_setoran)
    return db_setoran

@app.get("/setoran/", response_model=list[schemas.SetoranResponse])
def get_all_setoran(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    setoran_list = db.query(models.Setoran).all()
    result = []
    for s in setoran_list:
        bukti = db.query(models.BuktiPembayaran).filter(models.BuktiPembayaran.id_setoran == s.id_setoran).first()
        result.append({
            "id_setoran": s.id_setoran,
            "id_sales": s.id_sales,
            "id_user": s.id_user,
            "jumlah_pembayaran": s.jumlah_pembayaran,
            "tanggal_jatuh_tempo": s.tanggal_jatuh_tempo,
            "status_pembayaran": s.status_pembayaran,
            "tanggal_setoran": s.tanggal_setoran,
            "foto_struk": bukti.foto_struk if bukti else None
        })
    return result

@app.get("/setoran/sales/{id_sales}/")
def get_setoran_by_sales(id_sales: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    setoran_list = db.query(models.Setoran).filter(models.Setoran.id_sales == id_sales).all()
    result = []
    for s in setoran_list:
        bukti = db.query(models.BuktiPembayaran).filter(models.BuktiPembayaran.id_setoran == s.id_setoran).first()
        pegawai = db.query(models.User).filter(models.User.id_user == s.id_user).first()
        result.append({
            "id_setoran": s.id_setoran,
            "id_sales": s.id_sales,
            "id_user": s.id_user,
            "nama_pegawai": pegawai.nama_lengkap if pegawai else "N/A",
            "jumlah_pembayaran": s.jumlah_pembayaran,
            "tanggal_jatuh_tempo": s.tanggal_jatuh_tempo,
            "status_pembayaran": s.status_pembayaran,
            "tanggal_setoran": s.tanggal_setoran,
            "foto_struk": bukti.foto_struk if bukti else None
        })
    return result

@app.post("/setoran/upload/", response_model=schemas.SetoranResponse, status_code=status.HTTP_201_CREATED)
async def create_setoran_with_bukti(
    id_sales: int = Form(...),
    id_user: int = Form(...),
    jumlah_pembayaran: float = Form(...),
    tanggal_jatuh_tempo: str = Form(...),
    status_pembayaran: str = Form(...),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    sales = db.query(models.Sales).filter(models.Sales.id_sales == id_sales).first()
    if not sales:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
    
    tgl_tempo = date.fromisoformat(tanggal_jatuh_tempo)
    
    db_setoran = models.Setoran(
        id_sales=id_sales,
        id_user=id_user,
        jumlah_pembayaran=jumlah_pembayaran,
        tanggal_setoran=date.today(),
        tanggal_jatuh_tempo=tgl_tempo,
        status_pembayaran=status_pembayaran
    )
    db.add(db_setoran)
    db.commit()
    db.refresh(db_setoran)
    
    sales.sisa_bayar = max(0, sales.sisa_bayar - jumlah_pembayaran)
    if sales.sisa_bayar <= 0:
        sales.sisa_bayar = 0
    db.commit()
    
    if file:
        foto_url = await upload_to_supabase(file, db_setoran.id_setoran)
        db_bukti = models.BuktiPembayaran(id_setoran=db_setoran.id_setoran, foto_struk=foto_url)
        db.add(db_bukti)
        db.commit()
    
    return db_setoran


@app.post("/setoran/{id_setoran}/upload-bukti/")
async def upload_bukti_pembayaran(id_setoran: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    setoran_exists = db.query(models.Setoran).filter(models.Setoran.id_setoran == id_setoran).first()
    if not setoran_exists:
        raise HTTPException(status_code=404, detail="Data Setoran tidak ditemukan")

    foto_url = await upload_to_supabase(file, id_setoran)

    db_bukti = models.BuktiPembayaran(id_setoran=id_setoran, foto_struk=foto_url)
    db.add(db_bukti)
    db.commit()
    
    return {"message": "Bukti pembayaran berhasil diunggah", "path": foto_url}


# --- ENDPOINT REKAPITULASI/DASHBOARD ---

@app.get("/dashboard/rekapitulasi/")
def get_rekapitulasi_keuangan(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    semua_sales = db.query(models.Sales).all()
    semua_setoran = db.query(models.Setoran).all()
    
    total_sudah_bayar = sum(s.total_invoice - s.sisa_bayar for s in semua_sales)
    total_belum_bayar = sum(s.sisa_bayar for s in semua_sales)
    total_invoice = sum(s.total_invoice for s in semua_sales)
    
    top_sales = sorted(semua_sales, key=lambda s: s.sisa_bayar, reverse=True)[:5]
    top_sales_utang = [
        {"nama_sales": s.nama_sales, "sisa_bayar": s.sisa_bayar, "total_invoice": s.total_invoice}
        for s in top_sales if s.sisa_bayar > 0
    ]
    
    recent = db.query(models.Setoran).order_by(models.Setoran.id_setoran.desc()).limit(5).all()
    recent_setoran = []
    for s in recent:
        sales = db.query(models.Sales).filter(models.Sales.id_sales == s.id_sales).first()
        pegawai = db.query(models.User).filter(models.User.id_user == s.id_user).first()
        recent_setoran.append({
            "nama_sales": sales.nama_sales if sales else "N/A",
            "nama_pegawai": pegawai.nama_lengkap if pegawai else "N/A",
            "jumlah": s.jumlah_pembayaran,
            "tanggal": str(s.tanggal_setoran),
            "status": s.status_pembayaran
        })

    today = date.today()
    setoran_hari_ini = db.query(models.Setoran).filter(models.Setoran.tanggal_setoran == today).all()
    total_setoran_hari_ini = sum(s.jumlah_pembayaran for s in setoran_hari_ini)
    jumlah_setoran_hari_ini = len(setoran_hari_ini)

    return {
        "total_sudah_bayar": total_sudah_bayar,
        "total_belum_bayar": total_belum_bayar,
        "total_invoice": total_invoice,
        "jumlah_sales": len(semua_sales),
        "total_transaksi_setoran": len(semua_setoran),
        "total_pendapatan_setoran": total_sudah_bayar,
        "total_setoran_hari_ini": total_setoran_hari_ini,
        "jumlah_setoran_hari_ini": jumlah_setoran_hari_ini,
        "status_summary": {
            "lunas": sum(1 for s in semua_setoran if s.status_pembayaran == "Lunas"),
            "belum_lunas": sum(1 for s in semua_setoran if s.status_pembayaran == "Belum Lunas")
        },
        "top_sales_utang": top_sales_utang,
        "recent_setoran": recent_setoran
    }


# --- ENDPOINT AUTH & USER MANAGEMENT ---

@app.post("/auth/login")
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    if not bcrypt.checkpw(request.password.encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    if user.role != request.role:
        raise HTTPException(status_code=401, detail="Role tidak sesuai")
    
    token = base64.b64encode(f"{user.username}:{user.role}".encode()).decode()
    
    return {
        "token": token,
        "user": {
            "id_user": user.id_user,
            "username": user.username,
            "nama_lengkap": user.nama_lengkap,
            "role": user.role
        }
    }


@app.get("/users/", response_model=list[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.User).all()


@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    
    hashed = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    db_user = models.User(
        username=user.username,
        password=hashed,
        nama_lengkap=user.nama_lengkap,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.delete("/users/{id_user}")
def delete_user(id_user: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id_user == id_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.role == "Pemilik":
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus akun Pemilik")
    db.delete(user)
    db.commit()
    return {"message": "User berhasil dihapus"}


@app.put("/users/{id_user}")
def update_user(id_user: int, update: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id_user == id_user).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    if user.role == "Pemilik":
        raise HTTPException(status_code=400, detail="Tidak bisa mengubah akun Pemilik")
    if update.username and update.username != user.username:
        existing = db.query(models.User).filter(models.User.username == update.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username sudah digunakan")
        user.username = update.username
    if update.nama_lengkap:
        user.nama_lengkap = update.nama_lengkap
    if update.password:
        user.password = bcrypt.hashpw(update.password.encode(), bcrypt.gensalt()).decode()
    db.commit()
    db.refresh(user)
    return user


@app.on_event("startup")
def seed_admin():
    db = next(get_db())
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin:
        db_user = models.User(
            username="admin",
            password=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
            nama_lengkap="Pemilik Toko",
            role="Pemilik"
        )
        db.add(db_user)
        db.commit()
    db.close()
