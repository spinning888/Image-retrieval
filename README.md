# 🚀 XImageSearch — Django Image Retrieval System
## AI Image Retrieval Web

---

## 🏆 News
- [Jan.16] README refined for assignment delivery and repository distribution

---

## 📋 Project Overview

XImageSearch is a Django-based local **image-to-image retrieval** web system. It supports uploading a query image, extracting an embedding using **DINOv2 (ViT-B/14)**, and performing **cosine similarity search** against an offline-built gallery feature database to return **Top-K** results.

This repository is prepared for a **Python Programming course project**, emphasizing:
- Alignment with the assignment checklist (`dinov2_numpy.py` / `preprocess_image.py` / `debug.py` / Top-10 retrieval)
- A complete web workflow (upload → async retrieval → polling → history/favorites)
- Practical performance engineering (fast response) and an optional ONNX/DirectML backend

---

## ✨ Core Innovations

- **Asynchronous retrieval pipeline**: redirects to the results page immediately after upload; the frontend polls for task status/results (no blocking requests)
- **Top-K acceleration**: uses `argpartition` to select Top-K efficiently (avoids full sorting), keeping retrieval latency stable in milliseconds
- **Embedding reuse cache**: repeated searches on the same image can reuse embeddings to reduce redundant computation
- **Quality-tiered results view**: groups results by similarity ranges and supports threshold filtering for better interpretability
- **History & favorites loop**: history records are traceable; favorites support tags and fast filtering (demo-friendly)
- **Optional GPU / DirectML**: enables ONNX Runtime acceleration without breaking the CPU pipeline (Windows-friendly)

---

## ⚙️ Installation & Run

### 1️⃣ Install Dependencies

Run in the directory containing `requirements.txt`:

```bash
pip install -r requirements.txt
```

### ✅ Linux Setup (Optional, Recommended)

Tested on Ubuntu/Debian-like distributions. For CentOS/RHEL, replace `apt` with your package manager.

```bash
# 1) System dependencies
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential

# 2) Create & activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3) Upgrade pip & install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2️⃣ Prepare Gallery (Offline Feature Building)

By default, the system loads the following files from the upper-level `assignments/` directory as the retrieval database:
- `gallery_features.npy`
- `gallery_index.csv`

If you have not generated them yet, go to `assignments/` and run:

```bash
python build_gallery.py
```

### 3️⃣ Initialize & Run Web

```bash
# Enter the project root (where manage.py is located)
cd XImageSearch

# Initialize database
python manage.py migrate

# Start server
python manage.py runserver
```

Open: http://127.0.0.1:8000/

---

## 🧪 Assignment Requirement Checklist (Mandatory)

According to `assignments/readme.txt`, the key checkpoints are:

- Implement `resize_short_side` in `preprocess_image.py` (resize the short side to the target size while ensuring both sides are multiples of 14)
- Complete the DINOv2 NumPy forward inference in `dinov2_numpy.py`
- Run `assignments/debug.py` and compare with `assignments/demo_data/cat_dog_feature.npy` to ensure the numerical deviation is within an acceptable tolerance
- Web retrieval flow: upload image → preprocessing → embedding extraction → cosine similarity search → return Top-10 results

---

## 🧩 Optional: Run Embedding on GPU (Windows Recommended)

This project supports an optional ONNX Runtime backend only for query embedding extraction. The gallery features still come from the offline-built database.

### 1) Install runtime

- Windows (recommended):

```bash
pip install onnxruntime-directml
```

- NVIDIA CUDA (optional):

```bash
pip install onnxruntime-gpu
```

### 2) Provide an ONNX model file

You need a DINOv2 ViT-B/14 ONNX model that is consistent with the offline gallery build (same weights / same output dimension). Example:

`assignments/vit-dinov2-base.onnx`

### 3) Enable via environment variables

PowerShell example:

```powershell
$env:DINO_BACKEND='onnx'
$env:DINO_ONNX_PATH='C:\\...\\assignments\\vit-dinov2-base.onnx'
$env:DINO_ORT_PROVIDERS='DmlExecutionProvider,CPUExecutionProvider'
python manage.py runserver
```

---

## 🌐 Quick Navigation

- Homepage (upload/search): `/`
- Results page: `/results/`
- History list: `/history/`
- History detail: `/history/<record_id>/`
- Favorites: `/favorites/`

### APIs

- Results polling: `/api/results/`
- Remove history: `/api/history/remove/`
- Add favorite: `/api/favorite/add/`
- Remove favorite: `/api/favorite/remove/`

---

## 📁 Project Structure

```bash
XImageSearch/
├── manage.py                  # Django entry point
├── mysite/                    # Django project settings
│   ├── settings.py            # static/media/gallery/onnx env configuration
│   └── urls.py                # URL routing entry
├── image_search/              # Core app
│   ├── views.py               # upload, async retrieval, polling APIs, favorites/history
│   ├── search_engine.py       # feature loading and Top-K retrieval
│   ├── dinov2_onnx.py         # optional ONNX Runtime backend
│   ├── models.py              # History / Favorite models
│   ├── templates/image_search/# HTML templates
│   └── static/image_search/   # frontend JS/CSS
├── media/                     # uploaded images (local demo)
├── static/                    # project-level static assets (if any)
├── db.sqlite3                 # SQLite database
├── requirements.txt           # dependencies
└── README.md
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

(If `gallery_features.npy` / `gallery_index.csv` are missing, run `python build_gallery.py` in the upper-level `assignments/` first.)

---

## 🌟 Feature Summary

- Image upload → embedding extraction → Top-K similarity search
- Asynchronous execution + results polling
- Threshold filtering and score-range grouping
- History records (collapsible / lazy loading)
- Favorites (tag-supported)
- Optional ONNX Runtime / DirectML acceleration (CPU fallback available)

---

## 📜 License & Notice

This repository is provided for educational and assignment submission purposes.

Unless otherwise stated, the code is released under the MIT License (see the repository root `LICENSE`).

Third-party models, weights, and datasets (if any) are subject to their respective licenses and terms.

---

## ✨ Contact

If you encounter any issues, feel free to reach out.

Email: 2024150065@mails.szu.edu.cn
