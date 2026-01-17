import os
import csv
import numpy as np
import argparse
import time

from dinov2_numpy import Dinov2Numpy
from preprocess_image import resize_short_side

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff")


def iter_images(root):
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith(EXTS):
                yield os.path.join(dp, fn)


def build_gallery(
    images_root: str,
    weights_path: str = "vit-dinov2-base.npz",
    out_feats: str = "gallery_features.npy",
    out_index: str = "gallery_index.csv",
    batch_size: int = 8,
    max_images: int = 0,
    resume: bool = True,
    log_every: int = 200,
) -> None:
    base_dir = os.path.dirname(__file__)

    images_root_abs = images_root
    if not os.path.isabs(images_root_abs):
        images_root_abs = os.path.join(base_dir, images_root_abs)

    weights_abs = weights_path
    if not os.path.isabs(weights_abs):
        weights_abs = os.path.join(base_dir, weights_abs)

    out_feats_abs = out_feats
    if not os.path.isabs(out_feats_abs):
        out_feats_abs = os.path.join(base_dir, out_feats_abs)

    out_index_abs = out_index
    if not os.path.isabs(out_index_abs):
        out_index_abs = os.path.join(base_dir, out_index_abs)

    weights = np.load(weights_abs)
    vit = Dinov2Numpy(weights)

    all_paths = list(iter_images(images_root_abs))
    if max_images and max_images > 0:
        all_paths = all_paths[:max_images]

    processed = set()
    old_feats = None
    if resume and os.path.exists(out_index_abs) and os.path.exists(out_feats_abs):
        try:
            with open(out_index_abs, "r", encoding="utf-8") as f:
                r = csv.reader(f)
                next(r, None)
                for row in r:
                    if row:
                        processed.add(row[0])
            old_feats = np.load(out_feats_abs)
        except Exception:
            processed = set()
            old_feats = None

    paths = [p for p in all_paths if p not in processed]
    print(f"Found {len(all_paths)} images under {images_root_abs}", flush=True)
    if processed:
        print(f"Resume enabled: already processed={len(processed)}, remaining={len(paths)}", flush=True)

    feats_chunks = []
    paths_all = []
    failures = 0
    batches_done = 0

    batch_imgs = []
    batch_paths = []
    t0 = time.time()
    total = len(paths)

    if total == 0:
        print("Nothing to do.", flush=True)
        return

    if log_every <= 0:
        log_every = 200

    for i, p in enumerate(paths, 1):
        try:
            img = resize_short_side(p, 224)
            batch_imgs.append(img)
            batch_paths.append(p)

            if len(batch_imgs) >= batch_size:
                X = np.concatenate(batch_imgs, axis=0)
                F = vit(X)  # (B,768)
                feats_chunks.append(F.astype(np.float32, copy=False))
                paths_all.extend(batch_paths)
                batch_imgs.clear()
                batch_paths.clear()

                batches_done += 1
                # Print batch-level progress to avoid long silent periods
                if batches_done % 1 == 0:
                    done = len(paths_all)
                    print(
                        f"batch={batches_done} ok={done} scanned={i}/{total} failures={failures} elapsed={time.time()-t0:.1f}s",
                        flush=True,
                    )

        except Exception:
            failures += 1

        if i % log_every == 0:
            print(f"[{i}/{total}] elapsed={time.time()-t0:.1f}s failures={failures} ok={len(paths_all)} batches={batches_done}", flush=True)

    if batch_imgs:
        try:
            X = np.concatenate(batch_imgs, axis=0)
            F = vit(X)
            feats_chunks.append(F.astype(np.float32, copy=False))
            paths_all.extend(batch_paths)
        except Exception:
            failures += len(batch_imgs)

    feats_new = np.concatenate(feats_chunks, axis=0) if feats_chunks else np.zeros((0, 768), dtype=np.float32)
    if old_feats is not None and old_feats.size and feats_new.size:
        feats = np.concatenate([old_feats, feats_new], axis=0)
    elif old_feats is not None and old_feats.size:
        feats = old_feats
    else:
        feats = feats_new

    np.save(out_feats_abs, feats)

    if resume and os.path.exists(out_index_abs):
        mode = "a"
        header_needed = False
    else:
        mode = "w"
        header_needed = True

    with open(out_index_abs, mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header_needed:
            w.writerow(["path"])
        for p in paths_all:
            w.writerow([p])

    print(f"Done. new={len(paths_all)} total_feats={feats.shape} failures={failures} time={time.time()-t0:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Build gallery features from an image folder")
    parser.add_argument("--images_root", type=str, default="images", help="Image folder (default: assignments/images)")
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--max_images", type=int, default=0, help="Limit images (0=all)")
    parser.add_argument("--no_resume", action="store_true", help="Do not resume; rebuild from scratch")
    parser.add_argument("--out_feats", type=str, default="gallery_features.npy")
    parser.add_argument("--out_index", type=str, default="gallery_index.csv")
    parser.add_argument("--weights", type=str, default="vit-dinov2-base.npz")
    parser.add_argument("--log_every", type=int, default=200, help="Print progress every N images")
    args = parser.parse_args()

    build_gallery(
        images_root=args.images_root,
        weights_path=args.weights,
        out_feats=args.out_feats,
        out_index=args.out_index,
        batch_size=args.batch_size,
        max_images=args.max_images,
        resume=(not args.no_resume),
        log_every=args.log_every,
    )


if __name__ == "__main__":
    main()
