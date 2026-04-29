# Image Metamorphosis

**Platform Edukasi Pengolahan Citra Digital Interaktif**  
*Built for Pengolahan Citra dan Pola (PCP)*

![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-06B6D4?logo=tailwindcss&logoColor=white)

---

## Tentang Project

**Image Metamorphosis** adalah aplikasi web edukasi pengolahan citra digital yang dirancang untuk memvisualisasikan proses matematis di balik setiap operasi citra. Aplikasi ini tidak hanya menampilkan gambar "Before & After", tetapi juga menjelaskan **rumus matematis**, **matriks piksel**, **kernel**, dan **langkah perhitungan manual**.
### Fitur Utama

- **Interface Modern & Responsif** dengan tema dark elegant
- **Header** elegan dengan warna `#DFD0B8`
- **Sidebar** collapsible dengan animasi smooth
- **Before & After** comparison yang rapi
- **Penjelasan Edukasi Lengkap**:
  - Rumus LaTeX
  - Matriks piksel sample (3×3 / 5×5)
  - Kernel konvolusi
  - Langkah perhitungan manual piksel demi piksel
- **Drag & Drop** upload gambar
- **Real-time Processing** menggunakan Flask + OpenCV

---

## 🛠️ Tech Stack

### Frontend
- **React 18** + TypeScript
- **Vite** The Build Tool
- **Tailwind CSS** + Custom Design System
- **Framer Motion**
- **React KaTeX** 
- **Lucide React**

### Backend
- **Flask** (Python)
- **OpenCV** + **NumPy**
- **Flask-CORS**

---

## Fitur yang Diimplementasikan

### Dasar Pengolahan Citra
- Upload gambar + informasi resolusi
- Konversi ke Grayscale + visualisasi matriks piksel

### Operasi Aritmatika
- Image Blending (dengan slider α)
- Background Subtraction

### Operasi Geometri
- Rotasi, Scaling, Translasi, Flip (Horizontal/Vertical)

### Operasi Titik
- Brightness Adjustment
- Contrast Adjustment
- Negative Image
- Thresholding (Binary & Otsu)

### Operasi Spasial
- Mean Filter
- Median Filter
- Sobel Edge Detection (dengan penjelasan kernel & konvolusi manual)

### Multi
- Enhancement Pipeline lengkap (Brightness → Contrast → Sharpening → Denoising)

---

## Cara Menjalankan Project

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Backend (Flask)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
# source venv/bin/activate

pip install -r requirements.txt #Ini adalah Instal apa aja yang dibutuhkan
python app.py
