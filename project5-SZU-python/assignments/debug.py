import numpy as np
from dinov2_numpy import Dinov2Numpy
from preprocess_image import center_crop

def cosine_similarity(a, b, eps=1e-8):
    a = a / (np.linalg.norm(a) + eps)
    b = b / (np.linalg.norm(b) + eps)
    return np.dot(a, b)


# load model
weights = np.load("./assignments/vit-dinov2-base.npz")
vit = Dinov2Numpy(weights)

# load reference features
ref_data = np.load("./assignments/demo_data/cat_dog_feature.npy", allow_pickle=True)
cat_ref = ref_data[0]
dog_ref = ref_data[1]

# extract features
cat_feat = vit(center_crop("./assignments/demo_data/cat.jpg"))[0]
dog_feat = vit(center_crop("./assignments/demo_data/dog.jpg"))[0]

# cosine similarity
cat_sim = cosine_similarity(cat_feat, cat_ref)
dog_sim = cosine_similarity(dog_feat, dog_ref)

print("Cosine similarity:")
print(f"Cat: {cat_sim:.6f}")
print(f"Dog: {dog_sim:.6f}")
