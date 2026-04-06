import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def largest_empty_rectangle(mask):
    """
    求掩码中最大的空白矩形（mask=True 表示遮挡）
    返回 (x1, y1, x2, y2)
    """
    h, w = mask.shape
    height = np.zeros(w, dtype=int)
    max_area = 0
    best = (0,0,0,0)

    for y in range(h):
        # 更新高度数组
        for x in range(w):
            height[x] = height[x] + 1 if not mask[y, x] else 0

        # 单调栈求最大矩形
        stack = []
        for x in range(w + 1):
            h_cur = height[x] if x < w else 0
            while stack and h_cur < height[stack[-1]]:
                idx = stack.pop()
                ch = height[idx]
                ww = x if not stack else x - stack[-1] - 1
                area = ch * ww
                if area > max_area:
                    max_area = area
                    x1 = stack[-1] + 1 if stack else 0
                    y1 = y - ch + 1
                    x2 = x - 1
                    y2 = y
                    best = (x1, y1, x2, y2)
            stack.append(x)
    return best

def split_min_rectangles(mask):
    """
    将 mask 中 False 的区域切分成若干个矩形。
    每个矩形用 (最小行号, 最大行号, 最小列号, 最大列号) 表示，
    范围为左闭右开区间。
    """
    mask = mask.copy()
    rects = []

    while np.any(~mask):
        x1, y1, x2, y2 = largest_empty_rectangle(mask)
        # x 横轴方向, y 是纵轴方向
        rects.append( (int(y1),y2+1,int(x1),x2+1) )
        mask[y1:y2+1, x1:x2+1] = True

    return rects

def plot_partition(mask, rects=None):
    """
    可视化 mask 及其矩形切分结果。
    mask: 2D bool array, True 表示遮挡, False 表示空白
    rects: 切分结果列表, 若为 None 则自动调用 split_min_rectangles
    """

    if rects is None:
        rects = split_min_rectangles(mask)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左图: 原始 mask
    ax = axes[0]
    ax.imshow(mask.astype(int), cmap='gray', vmin=0, vmax=1, origin='upper')
    ax.set_title('Original Mask\n(white=True, black=False)')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')

    # 右图: 切分结果
    ax = axes[1]
    ax.imshow(np.ones_like(mask, dtype=float), cmap='gray', vmin=0, vmax=1, origin='upper')
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    for i, (r1, r2, c1, c2) in enumerate(rects):
        color = colors[i % len(colors)]
        rect_patch = patches.Rectangle(
            (c1 - 0.5, r1 - 0.5), c2 - c1, r2 - r1,
            linewidth=2, edgecolor='black', facecolor=color, alpha=0.6
        )
        ax.add_patch(rect_patch)
        ax.text(
            (c1 + c2) / 2 - 0.5, (r1 + r2) / 2 - 0.5,
            f'Rect {i}\n({r1},{r2},{c1},{c2})',
            ha='center', va='center', fontsize=7, fontweight='bold'
        )
    ax.set_title('Partition Result\n(row_min, row_max, col_min, col_max)')
    ax.set_xlabel('Column')
    ax.set_ylabel('Row')
    ax.set_xlim(-0.5, mask.shape[1] - 0.5)
    ax.set_ylim(mask.shape[0] - 0.5, -0.5)

    plt.tight_layout()
    plt.show()