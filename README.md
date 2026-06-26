# Sistem Manajemen Setoran Sales API

API untuk mengelola data sales, setoran, dan rekapitulasi keuangan toko grosir.

- **Base URL:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Database:** SQLite (`toko_grosir.db`)

---

## Daftar Endpoint

| Method | Path | Deskripsi |
|--------|------|-----------|
| `POST` | `/sales/` | Membuat data sales baru |
| `GET` | `/sales/` | Mengambil semua data sales |
| `POST` | `/setoran/` | Membuat setoran baru |
| `POST` | `/setoran/{id_setoran}/upload-bukti/` | Upload bukti pembayaran setoran |
| `GET` | `/dashboard/rekapitulasi/` | Rekapitulasi keuangan |

---

## 1. POST /sales/

Membuat data sales baru.

### Request Body (JSON)

| Field | Tipe | Required | Deskripsi |
|-------|------|----------|-----------|
| `nama_sales` | string | Ya | Nama sales |
| `no_telp` | string | Ya | Nomor telepon |
| `alamat` | string | Ya | Alamat sales |
| `jadwal_bayar` | string | Ya | Jadwal pembayaran (`Mingguan` / `Bulanan`) |

**Contoh Request:**
```json
{
  "nama_sales": "Budi Santoso",
  "no_telp": "081234567890",
  "alamat": "Jl. Merdeka No. 123, Jakarta",
  "jadwal_bayar": "Mingguan"
}
```

### Response (201 Created)

```json
{
  "id_sales": 1,
  "nama_sales": "Budi Santoso",
  "no_telp": "081234567890",
  "alamat": "Jl. Merdeka No. 123, Jakarta",
  "jadwal_bayar": "Mingguan"
}
```

### Status Codes

| Kode | Deskripsi |
|------|-----------|
| 201 | Sales berhasil dibuat |
| 422 | Validasi gagal (field required / tipe data salah) |

### Contoh cURL

```bash
curl -X POST http://localhost:8000/sales/ \
  -H "Content-Type: application/json" \
  -d '{
    "nama_sales": "Budi Santoso",
    "no_telp": "081234567890",
    "alamat": "Jl. Merdeka No. 123, Jakarta",
    "jadwal_bayar": "Mingguan"
  }'
```

---

## 2. GET /sales/

Mengambil semua data sales.

### Response (200 OK)

```json
[
  {
    "id_sales": 1,
    "nama_sales": "Budi Santoso",
    "no_telp": "081234567890",
    "alamat": "Jl. Merdeka No. 123, Jakarta",
    "jadwal_bayar": "Mingguan"
  }
]
```

### Status Codes

| Kode | Deskripsi |
|------|-----------|
| 200 | Berhasil mengambil data sales |

### Contoh cURL

```bash
curl -X GET http://localhost:8000/sales/
```

---

## 3. POST /setoran/

Membuat setoran baru. **Sales harus sudah ada** di database.

### Request Body (JSON)

| Field | Tipe | Required | Deskripsi |
|-------|------|----------|-----------|
| `id_sales` | integer | Ya | ID sales yang melakukan setoran |
| `id_user` | integer | Ya | ID pegawai yang mencatat setoran |
| `jumlah_pembayaran` | float | Ya | Jumlah pembayaran |
| `tanggal_jatuh_tempo` | date (YYYY-MM-DD) | Ya | Tanggal jatuh tempo |
| `status_pembayaran` | string | Ya | Status (`Lunas` / `Belum Lunas` / `Terlambat`) |

**Contoh Request:**
```json
{
  "id_sales": 1,
  "id_user": 1,
  "jumlah_pembayaran": 500000.0,
  "tanggal_jatuh_tempo": "2026-07-15",
  "status_pembayaran": "Belum Lunas"
}
```

### Response (201 Created)

```json
{
  "id_setoran": 1,
  "id_sales": 1,
  "id_user": 1,
  "jumlah_pembayaran": 500000.0,
  "tanggal_setoran": "2026-06-26",
  "tanggal_jatuh_tempo": "2026-07-15",
  "status_pembayaran": "Belum Lunas"
}
```

### Status Codes

| Kode | Deskripsi |
|------|-----------|
| 201 | Setoran berhasil dibuat |
| 404 | Sales dengan `id_sales` yang diberikan tidak ditemukan |
| 422 | Validasi gagal (field required / tipe data salah) |

### Contoh cURL

```bash
curl -X POST http://localhost:8000/setoran/ \
  -H "Content-Type: application/json" \
  -d '{
    "id_sales": 1,
    "id_user": 1,
    "jumlah_pembayaran": 500000.0,
    "tanggal_jatuh_tempo": "2026-07-15",
    "status_pembayaran": "Belum Lunas"
  }'
```

### Catatan

- Field `tanggal_setoran` diisi otomatis dengan tanggal hari ini.

---

## 4. POST /setoran/{id_setoran}/upload-bukti/

Upload file bukti pembayaran (foto struk) untuk setoran tertentu.

### Path Parameter

| Parameter | Tipe | Deskripsi |
|-----------|------|-----------|
| `id_setoran` | integer | ID setoran yang akan diupload buktinya |

### Request (multipart/form-data)

| Field | Tipe | Required | Deskripsi |
|-------|------|----------|-----------|
| `file` | file (UploadFile) | Ya | File gambar bukti pembayaran |

### Response (200 OK)

```json
{
  "message": "Bukti pembayaran berhasil diunggah",
  "path": "uploaded_struk/1_struk.jpg"
}
```

### Status Codes

| Kode | Deskripsi |
|------|-----------|
| 200 | Bukti berhasil diupload |
| 404 | Setoran dengan `id_setoran` yang diberikan tidak ditemukan |
| 422 | File tidak disertakan |

### Contoh cURL

```bash
curl -X POST http://localhost:8000/setoran/1/upload-bukti/ \
  -F "file=@/path/to/foto_struk.jpg"
```

### Catatan

- File disimpan di folder `uploaded_struk/` dengan format `{id_setoran}_{original_filename}`.
- Path file disimpan di tabel `bukti_pembayaran`.

---

## 5. GET /dashboard/rekapitulasi/

Menampilkan rekapitulasi keuangan: total pendapatan, jumlah transaksi, dan ringkasan status pembayaran.

### Response (200 OK)

```json
{
  "total_pendapatan_setoran": 1500000.0,
  "total_transaksi_setoran": 3,
  "status_summary": {
    "lunas": 1,
    "belum_lunas": 2
  }
}
```

### Status Codes

| Kode | Deskripsi |
|------|-----------|
| 200 | Berhasil mengambil rekapitulasi |

### Contoh cURL

```bash
curl -X GET http://localhost:8000/dashboard/rekapitulasi/
```

### Catatan

- `total_pendapatan_setoran` adalah jumlah dari semua `jumlah_pembayaran` di tabel setoran.
- `status_summary.lunas` adalah jumlah setoran dengan status `Lunas`.
- `status_summary.belum_lunas` adalah jumlah setoran dengan status `Belum Lunas`.

---

## Entity Relationship

| Model | Tabel | Primary Key |
|-------|-------|-------------|
| User | `users` | `id_user` |
| Sales | `sales` | `id_sales` |
| Setoran | `setoran` | `id_setoran` |
| BuktiPembayaran | `bukti_pembayaran` | `id_bukti` |

**Relasi:**
- `setoran.id_sales` → `sales.id_sales` (many-to-one)
- `setoran.id_user` → `users.id_user` (many-to-one)
- `bukti_pembayaran.id_setoran` → `setoran.id_setoran` (one-to-one)

---

## Cara Menjalankan

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
