# 🚀 XImageSearch — Django 图搜图系统
## AI Image Retrieval Web

---

## 🏆 News
- [Jan.16] README 模板化整理与实验交付版本

---

## 📋 Project Overview

XImageSearch 是一个基于 Django 的本地网页“以图搜图”系统：支持上传查询图片，使用 DINOv2 (ViT-B/14) 提取 embedding，与离线构建的图库特征做余弦相似度检索，返回 Top-K 结果。

本项目面向 **Python 程序设计课程实验**，强调：
- 与实验 readme 任务要求对齐（`dinov2_numpy.py` / `preprocess_image.py` / `debug.py` / 检索 Top-10）
- Web 端交互完整（上传→异步检索→结果页轮询刷新→历史/收藏）
- 性能优化（尽快出结果）与可选 GPU 后端（ONNX Runtime / DirectML）

---

## ✨ Core Innovations

- **异步检索链路**：上传后立即返回结果页，通过轮询接口获取任务状态与结果（避免请求阻塞）
- **TopK 加速**：用 `argpartition` 快速取 Top-K（避免全量排序），检索耗时稳定在毫秒级
- **Embedding 复用缓存**：同一图片重复搜索可直接复用 embedding（加速重复查询）
- **结果质量分层展示**：按相似度区间分组与计数，支持阈值过滤（更直观可解释）
- **收藏/历史完整闭环**：收藏支持 tags，历史页支持折叠与懒加载（易于演示与复盘）
- **可选 GPU / DirectML**：在不破坏 CPU 版本的前提下支持 ONNX Runtime 加速（Windows 友好）

---

## ⚙️ Installation & Run

### 1️⃣ Install Dependencies

在本目录（含 `requirements.txt`）执行：
```bash
pip install -r requirements.txt
```

### 2️⃣ Prepare Gallery (离线构建图库特征)

系统默认从上级 `assignments/` 读取以下文件作为检索底库：
- `gallery_features.npy`
- `gallery_index.csv`

注意：按 GitHub 项目规范，本仓库默认 **不提交大体积图片数据/特征产物/模型权重**。你需要自行准备：
- `assignments/vit-dinov2-base.npz`（DINOv2 ViT-B/14 权重）
- `assignments/images/`（图库图片目录）

如果你还没生成它们，请到 `assignments/` 目录执行：
```bash
python build_gallery.py
```

如需扩展图库，请自行准备图片集放入 `assignments/images/` 后再运行建库。

### 3️⃣ Initialize & Run Web

```bash
# 进入项目根目录（manage.py 所在目录）
cd XImageSearch

# 初始化数据库
python manage.py migrate

# 启动服务
python manage.py runserver
```

访问： http://127.0.0.1:8000/

---

## 🧪 实验任务对齐（必做）

按上级目录 `assignments/readme.txt` 的要求，本实验核心检查点包括：
- 完成 `preprocess_image.py` 中的 `resize_short_side`（短边缩放到目标尺寸，同时保证边长为 14 的倍数）
- 完成 `dinov2_numpy.py` 的 DINOv2 NumPy 前向推理
- 运行 `assignments/debug.py`，并与 `assignments/demo_data/cat_dog_feature.npy` 对比，确保误差在可接受范围内
- Web 检索：上传图片 → 预处理 → 提取 embedding → 与图库特征计算相似度 → 返回 Top-10

---

## 🧩 Optional: Run Embedding on GPU (Windows recommended)

本项目支持可选 ONNX Runtime 后端（仅影响“查询图 embedding”，图库特征仍来自离线构建）。

### 1) Install runtime
- Windows（推荐）：
```bash
pip install onnxruntime-directml
```
- NVIDIA CUDA（可选）：
```bash
pip install onnxruntime-gpu
```

### 2) Provide an ONNX model file
你需要一个 **与离线构建图库时同权重/同输出维度** 的 DINOv2 ViT-B/14 ONNX 模型。
例如放在：`assignments/vit-dinov2-base.onnx`

### 3) Enable via environment variables
PowerShell 示例：
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
│   ├── settings.py            # static/media/gallery/onnx env 配置
│   └── urls.py                # 路由入口
├── image_search/              # 核心 App
│   ├── views.py               # 上传、异步检索、轮询接口、收藏/历史
│   ├── search_engine.py       # 特征加载与 TopK 检索
│   ├── dinov2_onnx.py         # ONNX Runtime 后端（可选）
│   ├── models.py              # History / Favorite 等
│   ├── templates/image_search/# 页面模板
│   └── static/image_search/   # 前端 JS/CSS
├── media/                     # 上传图片（本地演示）
├── static/                    # 项目级静态资源（如有）
├── db.sqlite3                 # SQLite 数据库
├── requirements.txt           # 依赖
└── README.md
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

（首次使用如果没有 `gallery_features.npy` / `gallery_index.csv`，先到上级 `assignments/` 跑 `python build_gallery.py`。）

---

## 🌟 Feature Summary

- 图像上传 → embedding → Top-K 相似检索
- 异步执行 + 结果页轮询刷新
- 阈值过滤、相似度分段展示
- 历史记录（折叠/懒加载）
- 收藏（支持 tags）
- 可选 ONNX Runtime / DirectML 加速（CPU 自动回退）

---

## ✨ Contact

Any issues, feel free to contact.

Email: 2024150065@mails.szu.edu.cn
