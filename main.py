from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import date
import shutil
import os
import bcrypt
import base64

import models, schemas
from database import engine, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Membuat tabel otomatis di SQLite jika belum ada
models.Base.metadata.create_all(bind=engine)


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

# Konfigurasi CORS agar React frontend bisa mengakses API ini nanti
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder untuk menyimpan file upload bukti pembayaran
UPLOAD_DIR = "uploaded_struk"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    return FileResponse(file_path)

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


# --- ENDPOINT FOR SETORAN (Kasir/Pegawai) ---

@app.post("/setoran/", response_model=schemas.SetoranResponse, status_code=status.HTTP_201_CREATED)
def create_setoran(setoran: schemas.SetoranCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Validasi apakah sales ada
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
    # Validasi apakah sales ada
    sales = db.query(models.Sales).filter(models.Sales.id_sales == id_sales).first()
    if not sales:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
    
    # Convert string ke date object
    tgl_tempo = date.fromisoformat(tanggal_jatuh_tempo)
    
    # Buat setoran
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
    
    # Update sisa bayar
    sales.sisa_bayar = max(0, sales.sisa_bayar - jumlah_pembayaran)
    if sales.sisa_bayar <= 0:
        sales.sisa_bayar = 0
    db.commit()
    
    # Upload bukti jika ada
    if file:
        file_location = f"{UPLOAD_DIR}/{db_setoran.id_setoran}_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        db_bukti = models.BuktiPembayaran(id_setoran=db_setoran.id_setoran, foto_struk=file_location)
        db.add(db_bukti)
        db.commit()
    
    return db_setoran


# --- ENDPOINT UPLOAD BUKTI (Kasir/Pegawai di Sprint 2) ---

@app.post("/setoran/{id_setoran}/upload-bukti/")
async def upload_bukti_pembayaran(id_setoran: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Pastikan data setoran ada
    setoran_exists = db.query(models.Setoran).filter(models.Setoran.id_setoran == id_setoran).first()
    if not setoran_exists:
        raise HTTPException(status_code=404, detail="Data Setoran tidak ditemukan")

    # Path penyimpanan file
    file_location = f"{UPLOAD_DIR}/{id_setoran}_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Simpan path file ke database
    db_bukti = models.BuktiPembayaran(id_setoran=id_setoran, foto_struk=file_location)
    db.add(db_bukti)
    db.commit()
    
    return {"message": "Bukti pembayaran berhasil diunggah", "path": file_location}


# --- ENDPOINT REKAPITULASI/DASHBOARD (Pemilik di Sprint 3) ---

@app.get("/dashboard/rekapitulasi/")
def get_rekapitulasi_keuangan(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    semua_sales = db.query(models.Sales).all()
    semua_setoran = db.query(models.Setoran).all()
    
    total_sudah_bayar = sum(s.total_invoice - s.sisa_bayar for s in semua_sales)
    total_belum_bayar = sum(s.sisa_bayar for s in semua_sales)
    total_invoice = sum(s.total_invoice for s in semua_sales)
    
    # Top 5 sales dengan sisa bayar terbesar
    top_sales = sorted(semua_sales, key=lambda s: s.sisa_bayar, reverse=True)[:5]
    top_sales_utang = [
        {"nama_sales": s.nama_sales, "sisa_bayar": s.sisa_bayar, "total_invoice": s.total_invoice}
        for s in top_sales if s.sisa_bayar > 0
    ]
    
    # 5 setoran terakhir dengan nama pegawai
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

    # Setoran hari ini
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