1. How to debug
- Complete dinov2_numpy.py
- Run debug.py
- Check output, i.e., compare your extracted features with the reference (./demo_data/cat_dog_feature.npy). Make sure the difference is within a small numerical tolerance.

2. Image retrieval
- Cownload 10,000+ web images (data.csv) to build the gallery set
- Finish 'resize_short_side' in preprocess_image.py. The function must correctly resize images of different resolutions such that the shorter side becomes the target size (e.g., 224). Meanwhile, both sides should be the multiple of 14
- Extract features for all gallery images via your ViT (dinov2_numpy.py)
- When user upload an image, preprocess → extract features, compute similarity with all gallery features (e.g., cosine similarity or L2 distance), and return the Top-10 most similar images as search results

3. (Optional) Run embedding on GPU (Windows recommended)
- The web app (assignments/XImageSearch) now supports an optional ONNX Runtime backend for query embedding.
- IMPORTANT: The ONNX model must match the same DINOv2 weights used to build gallery_features.npy, otherwise retrieval quality will be wrong.

3.1 Install runtime
- Windows (most compatible): pip install onnxruntime-directml
- NVIDIA CUDA (optional): pip install onnxruntime-gpu

3.2 Provide an ONNX model file
- You need a DINOv2 ViT-B/14 ONNX model that outputs an embedding vector.
- Put it somewhere on disk, e.g. assignments/vit-dinov2-base.onnx

3.3 Enable ONNX backend via environment variables
- DINO_BACKEND=onnx
- DINO_ONNX_PATH=...path/to/model.onnx
- (optional) DINO_ORT_PROVIDERS=DmlExecutionProvider,CPUExecutionProvider

Example (PowerShell):
- $env:DINO_BACKEND='onnx'
- $env:DINO_ONNX_PATH='C:\\...\\vit-dinov2-base.onnx'
- $env:DINO_ORT_PROVIDERS='DmlExecutionProvider,CPUExecutionProvider'
- python manage.py runserver