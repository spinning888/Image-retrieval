import numpy as np

from scipy.ndimage import zoom

def gelu(x):
    x = x.astype(np.float32, copy=False)
    # float32 constants to avoid implicit float64 upcast
    c0 = np.float32(0.5)
    c1 = np.float32(1.0)
    c2 = np.float32(0.044715)
    k = np.float32(np.sqrt(2.0 / np.pi))
    x3 = x * x * x
    return c0 * x * (c1 + np.tanh(k * (x + c2 * x3)))

class Embeddings:
    def __init__(self, weights):
        """
        NumPy 实现的 Dinov2 Embeddings 层。

        参数：
        - weights: 权重字典，包含：
            - 'cls_token': 形状为 (1, 1, hidden_size)
            - 'position_embeddings': 形状为 (1, num_patches + 1, hidden_size)
        """
        self.hidden_size = 768 # D
        self.patch_size  = 14  # ps

        self.cls_token           = weights["embeddings.cls_token"] # (1, 1, D)
        self.position_embeddings = weights["embeddings.position_embeddings"] # (1, N+1, D)
        self.patch_embed_w       = weights["embeddings.patch_embeddings.projection.weight"].reshape(768, -1).T
        self.patch_embed_b       = weights["embeddings.patch_embeddings.projection.bias"].reshape(768, 1).T

    def pixel2patches(self, pixel_values): 
        B, C, H, W = pixel_values.shape
        assert H % self.patch_size == 0 and W % self.patch_size == 0

        patches = []
        for i in range(0, H, self.patch_size):
            for j in range(0, W, self.patch_size):
                patch = pixel_values[:, :, i:i+self.patch_size, j:j+self.patch_size].reshape(B, -1)
                patches.append(patch)

        patches = np.stack(patches, axis=1)  # shape: (B, num_patches, patch_dim)
        return patches

    def interpolate_pos_encoding(self, embeddings, height, width):
        # 将位置编码插值到与当前输入大小匹配
        # 输入 embeddings 仅用于获取 batch 大小 B
        B = embeddings.shape[0]

        cls_pos = self.position_embeddings[:, :1, :]   # (1, 1, D)
        patch_pos = self.position_embeddings[:, 1:, :]  # (1, N0, D)

        # 原始网格大小（训练时的 patch 网格，如 16x16）
        N0 = patch_pos.shape[1]
        grid_old = int(np.sqrt(N0))
        assert grid_old * grid_old == N0, "Position embeddings patch part is not a square grid"

        # 目标网格大小（当前输入的 patch 网格）
        h_new = height // self.patch_size
        w_new = width  // self.patch_size

        if h_new == grid_old and w_new == grid_old:
            # 直接复用，无需插值
            return np.tile(self.position_embeddings, (B, 1, 1))

        # (1, N0, D) -> (grid_old, grid_old, D)
        patch_pos_grid = patch_pos.reshape(1, grid_old, grid_old, -1)[0]

        # 使用线性插值(order=1)在空间维度缩放到 (h_new, w_new) 以提升速度
        zoom_factors = (h_new / grid_old, w_new / grid_old, 1.0)
        patch_pos_resized = zoom(patch_pos_grid, zoom_factors, order=1)

        # 展平并重新拼接 cls 的位置编码
        patch_pos_resized = patch_pos_resized.reshape(1, h_new * w_new, -1)  # (1, h*w, D)
        pos_embed = np.concatenate([cls_pos, patch_pos_resized], axis=1)     # (1, h*w+1, D)

        # 扩展到 batch 维度
        pos_embed = np.tile(pos_embed, (B, 1, 1))
        return pos_embed

    def __call__(self, pixel_values):
        B, _, H, W = pixel_values.shape

        patch_values = self.pixel2patches(pixel_values) # (B, C, H, W) -> (B, h*w, C*ps**2), h=H//ps, w=W//ps
        
        # (B, h*w, C*ps**2) @ (C*ps**2, D) + (1, D) -> (B, h*w, D)
        embeddings = patch_values @ self.patch_embed_w + self.patch_embed_b
        
        cls_token  = np.tile(self.cls_token, (B, 1, 1)) # (1, 1, D) -> (B, 1, D)
        embeddings = np.concatenate([cls_token, embeddings], axis=1) # (B, h*w+1, D)

        pos_embed  = self.interpolate_pos_encoding(embeddings, H, W) # (B, N+1, D) -> (B, h*w+1, D)
        
        embeddings = embeddings + pos_embed
        return embeddings

class LayerNorm:
    def __init__(self, weight, bias, eps=1e-6):
        self.weight = weight
        self.bias   = bias
        self.eps    = eps

    def __call__(self, x, ):
        mean = x.mean(-1, keepdims=True)
        var  = x.var(-1, keepdims=True)
        norm = (x - mean) / np.sqrt(var + self.eps)
        out = norm * self.weight + self.bias
        return out.astype(np.float32, copy=False)

class LayerScale: 
    def __init__(self, lambda1): 
        self.lambda1 = lambda1

    def __call__(self, x): 
        return x * self.lambda1

class Linear:
    def __init__(self, weight, bias):
        self.weight = weight
        self.bias   = bias

    def __call__(self, x):
        return x @ self.weight.T + self.bias

class SingleHeadAttention:
    def __init__(self, config, prefix, weights):
        q_w = weights[f"{prefix}.attention.query.weight"]
        q_b = weights[f"{prefix}.attention.query.bias"]
        k_w = weights[f"{prefix}.attention.key.weight"]
        k_b = weights[f"{prefix}.attention.key.bias"]
        v_w = weights[f"{prefix}.attention.value.weight"]
        v_b = weights[f"{prefix}.attention.value.bias"]
        o_w = weights[f"{prefix}.output.dense.weight"]
        o_b = weights[f"{prefix}.output.dense.bias"]

        self.q_proj = Linear(q_w, q_b)
        self.k_proj = Linear(k_w, k_b)
        self.v_proj = Linear(v_w, v_b)
        self.out_proj = Linear(o_w, o_b)

    def __call__(self, x):
        q = self.q_proj(x) # (B, h*w+1, D)
        k = self.k_proj(x) # (B, h*w+1, D)
        v = self.v_proj(x) # (B, h*w+1, D)
        att = np.matmul(q, k.transpose(0,2,1)) / np.sqrt(self.hidden_size) # (B, h*w+1, h*w+1)
        att = softmax(att)
        out = np.matmul(att, v) # (B, h*w+1, D)
        return self.out_proj(out)

class MultiHeadAttention:
    def __init__(self, config, prefix, weights):
        self.num_heads = config['num_heads']
        self.head_dim = config['hidden_size'] // self.num_heads

        q_w = weights[f"{prefix}.attention.query.weight"]
        q_b = weights[f"{prefix}.attention.query.bias"]
        k_w = weights[f"{prefix}.attention.key.weight"]
        k_b = weights[f"{prefix}.attention.key.bias"]
        v_w = weights[f"{prefix}.attention.value.weight"]
        v_b = weights[f"{prefix}.attention.value.bias"]
        o_w = weights[f"{prefix}.output.dense.weight"]
        o_b = weights[f"{prefix}.output.dense.bias"]

        self.q_proj   = Linear(q_w, q_b)
        self.k_proj   = Linear(k_w, k_b)
        self.v_proj   = Linear(v_w, v_b)
        self.out_proj = Linear(o_w, o_b)

    def __call__(self, x):
        # 多头自注意力前向传播（无 mask）
        B, S, D = x.shape

        q = self.q_proj(x)  # (B, S, D)
        k = self.k_proj(x)  # (B, S, D)
        v = self.v_proj(x)  # (B, S, D)

        # 分头： (B, S, D) -> (B, num_heads, S, head_dim)
        q = q.reshape(B, S, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        k = k.reshape(B, S, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)
        v = v.reshape(B, S, self.num_heads, self.head_dim).transpose(0, 2, 1, 3)

        # 注意力打分： (B, h, S, hd) @ (B, h, hd, S) -> (B, h, S, S)
        scale = 1.0 / np.sqrt(self.head_dim)
        attn_scores = np.matmul(q, k.transpose(0, 1, 3, 2)) * scale
        attn = softmax(attn_scores, axis=-1)

        # 聚合 V： (B, h, S, S) @ (B, h, S, hd) -> (B, h, S, hd)
        out = np.matmul(attn, v)

        # 合并头： (B, h, S, hd) -> (B, S, D)
        out = out.transpose(0, 2, 1, 3).reshape(B, S, D)

        # 输出线性层
        return self.out_proj(out)

class MLP:
    def __init__(self, prefix, weights):
        w1 = weights[f"{prefix}.mlp.fc1.weight"]
        b1 = weights[f"{prefix}.mlp.fc1.bias"]
        w2 = weights[f"{prefix}.mlp.fc2.weight"]
        b2 = weights[f"{prefix}.mlp.fc2.bias"]

        self.fc1 = Linear(w1, b1)
        self.fc2 = Linear(w2, b2)

    def __call__(self, x):
        return self.fc2(gelu(self.fc1(x)))

def softmax(x, axis=-1):
    x = x.astype(np.float32, copy=False)
    x_max = np.max(x, axis=axis, keepdims=True)
    x_exp = np.exp(x - x_max)
    x_sum = np.sum(x_exp, axis=axis, keepdims=True)
    return x_exp / x_sum

class TransformerBlock:
    def __init__(self, config, idx, weights):
        prefix = f"encoder.layer.{idx}"
        
        self.norm1 = LayerNorm(weights[f"{prefix}.norm1.weight"], weights[f"{prefix}.norm1.bias"])
        self.scale1 = LayerScale(weights[f"{prefix}.layer_scale1.lambda1"])
        self.attn = MultiHeadAttention(config, f"{prefix}.attention", weights)

        self.norm2 = LayerNorm(weights[f"{prefix}.norm2.weight"], weights[f"{prefix}.norm2.bias"])
        self.scale2 = LayerScale(weights[f"{prefix}.layer_scale2.lambda1"])
        self.mlp = MLP(f"{prefix}", weights)

    def __call__(self, x):
        x = x + self.scale1(self.attn(self.norm1(x)))
        x = x + self.scale2(self.mlp(self.norm2(x)))
        return x

class Dinov2Numpy:
    def __init__(self, weights, config=None):
        self.weights = weights
        self.config = config or {
            "hidden_size": 768,
            "num_heads": 12,
            "num_layers": 12,
            "patch_size": 14,
        }

        self.embeddings = Embeddings(weights)
        self.blocks     = [TransformerBlock(self.config, i, weights) for i in range(self.config["num_layers"])]
        self.norm       = LayerNorm(weights["layernorm.weight"], weights["layernorm.bias"])

    def __call__(self, pixel_values):
        pos_embed = self.embeddings(pixel_values)
        for blk in self.blocks:
            pos_embed = blk(pos_embed)
        pos_embed = self.norm(pos_embed)
        return pos_embed[:, 0]
