import csv
import sys
import numpy as np
from dinov2_numpy import Dinov2Numpy
from preprocess_image import resize_short_side


def load_gallery():
    feats = np.load("gallery_features.npy")  # (N, 768)
    paths = []
    with open("gallery_index.csv", "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if row:
                paths.append(row[0])
    return feats, paths


def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-8)
    b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-8)
    return a @ b.T


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_image.py <query_image_path>")
        return
    qpath = sys.argv[1]

    weights = np.load("vit-dinov2-base.npz")
    vit = Dinov2Numpy(weights)
    qx = resize_short_side(qpath, target_size=224)
    qf = vit(qx)[None]  # (1, 768)

    feats, paths = load_gallery()
    sims = cosine_sim(qf, feats)[0]
    idx = np.argsort(-sims)[:10]
    print("Top-10 similar images:")
    for i in idx:
        print(paths[i], float(sims[i]))


if __name__ == "__main__":
    main()
