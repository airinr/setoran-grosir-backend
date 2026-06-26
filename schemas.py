from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

# Schema Dasar untuk Sales
class SalesBase(BaseModel):
    nama_sales: str
    no_telp: str
    alamat: str
    jadwal_bayar: str

class SalesCreate(SalesBase):
    pass

class SalesResponse(SalesBase):
    id_sales: int

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

    class Config:
        from_attributes = True