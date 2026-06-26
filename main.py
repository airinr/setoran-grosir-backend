from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import shutil
import os

import models, schemas
from database import engine, get_db

# Membuat tabel otomatis di SQLite jika belum ada
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistem Manajemen Setoran Sales API")

# Konfigurasi CORS agar React frontend bisa mengakses API ini nanti
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Di produksi, ganti dengan URL spesifik React Anda
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder untuk menyimpan file upload bukti pembayaran
UPLOAD_DIR = "uploaded_struk"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- ENDPOINT FOR SALES ---

@app.post("/sales/", response_model=schemas.SalesResponse, status_code=status.HTTP_201_CREATED)
def create_sales(sales: schemas.SalesCreate, db: Session = Depends(get_db)):
    db_sales = models.Sales(**sales.model_dump())
    db.add(db_sales)
    db.commit()
    db.refresh(db_sales)
    return db_sales

@app.get("/sales/", response_model=list[schemas.SalesResponse])
def get_all_sales(db: Session = Depends(get_db)):
    return db.query(models.Sales).all()


# --- ENDPOINT FOR SETORAN (Kasir/Pegawai) ---

@app.post("/setoran/", response_model=schemas.SetoranResponse, status_code=status.HTTP_201_CREATED)
def create_setoran(setoran: schemas.SetoranCreate, db: Session = Depends(get_db)):
    # Validasi apakah sales ada
    sales_exists = db.query(models.Sales).filter(models.Sales.id_sales == setoran.id_sales).first()
    if not sales_exists:
        raise HTTPException(status_code=404, detail="Sales tidak ditemukan")
        
    db_setoran = models.Setoran(**setoran.model_dump())
    db.add(db_setoran)
    db.commit()
    db.refresh(db_setoran)
    return db_setoran


# --- ENDPOINT UPLOAD BUKTI (Kasir/Pegawai di Sprint 2) ---

@app.post("/setoran/{id_setoran}/upload-bukti/")
async def upload_bukti_pembayaran(id_setoran: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
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
def get_rekapitulasi_keuangan(db: Session = Depends(get_db)):
    # Mengambil semua setoran untuk kalkulasi otomatis arus kas
    semua_setoran = db.query(models.Setoran).all()
    
    total_uang_masuk = sum(item.jumlah_pembayaran for item in semua_setoran)
    total_transaksi = len(semua_setoran)
    
    # Menghitung jumlah status bayar
    lunas = db.query(models.Setoran).filter(models.Setoran.status_pembayaran == "Lunas").count()
    belum_lunas = db.query(models.Setoran).filter(models.Setoran.status_pembayaran == "Belum Lunas").count()

    return {
        "total_pendapatan_setoran": total_uang_masuk,
        "total_transaksi_setoran": total_transaksi,
        "status_summary": {
            "lunas": lunas,
            "belum_lunas": belum_lunas
        }
    }