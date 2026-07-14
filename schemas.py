from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

# Schema Dasar untuk Sales
class SalesBase(BaseModel):
    nama_sales: str
    no_telp: str
    alamat: str
    jadwal_bayar: str
    total_invoice: float = 0
    periode_minggu: int = 4

class SalesCreate(SalesBase):
    pass

class SalesResponse(SalesBase):
    id_sales: int
    sisa_bayar: float = 0

    class Config:
        from_attributes = True

# Schema Dasar untuk Setoran
class SetoranBase(BaseModel):
    id_sales: int
    id_user: int
    jumlah_pembayaran: float
    tanggal_jatuh_tempo: date
    status_pembayaran: str

class SetoranCreate(SetoranBase):
    pass

class SetoranResponse(SetoranBase):
    id_setoran: int
    tanggal_setoran: date
    foto_struk: Optional[str] = None

    class Config:
        from_attributes = True

# Schema untuk User/Akun
class UserCreate(BaseModel):
    username: str
    password: str
    nama_lengkap: str
    role: str

class UserResponse(BaseModel):
    id_user: int
    username: str
    nama_lengkap: str
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    nama_lengkap: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
    role: str