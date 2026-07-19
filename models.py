from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    nama_lengkap = Column(String)
    role = Column(String)

    setoran_dicatat = relationship("Setoran", back_populates="pegawai")

class Sales(Base):
    __tablename__ = "sales"

    id_sales = Column(Integer, primary_key=True, index=True)
    nama_sales = Column(String, index=True)
    no_telp = Column(String)
    alamat = Column(String)
    jadwal_bayar = Column(String)
    total_invoice = Column(Float, default=0)
    periode_minggu = Column(Integer, default=4)
    sisa_bayar = Column(Float, default=0)

    daftar_setoran = relationship("Setoran", back_populates="sales")

class Setoran(Base):
    __tablename__ = "setoran"

    id_setoran = Column(Integer, primary_key=True, index=True)
    id_sales = Column(Integer, ForeignKey("sales.id_sales"))
    id_user = Column(Integer, ForeignKey("users.id_user"))
    tanggal_setoran = Column(Date)
    jumlah_pembayaran = Column(Float)
    tanggal_jatuh_tempo = Column(Date)
    status_pembayaran = Column(String)

    sales = relationship("Sales", back_populates="daftar_setoran")
    pegawai = relationship("User", back_populates="setoran_dicatat")
    bukti = relationship("BuktiPembayaran", uselist=False, back_populates="setoran")

class BuktiPembayaran(Base):
    __tablename__ = "bukti_pembayaran"

    id_bukti = Column(Integer, primary_key=True, index=True)
    id_setoran = Column(Integer, ForeignKey("setoran.id_setoran"))
    foto_struk = Column(String)
    tanggal_upload = Column(DateTime)

    setoran = relationship("Setoran", back_populates="bukti")
