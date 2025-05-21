import math
import numpy as np
from network.layer import hnnLayer

class hnn():
    net_size = 100  # 例如 100 表示 10×10
    num_imgs = 5
    side = int(np.sqrt(net_size))  # 图像边长
    selected_patterns = None
    processed_patterns = None
    damaged_patterns = None

    def __init__(self,chip):
        """
            加载数据集,进行预处理
        """
        self.processed_patterns = np.load("./data/hnn/processed_patterns.npy")
        # dl = DataLoader()
        # weight = dl.load_csv("../data/hnn/HNN_W_matrix_origin.csv")

        self.layer=hnnLayer(chip=chip,weight_target=0,weight_min=-0.17,weight_max=0.17,cond_min=0,cond_max=1100,cond_reference=550)
        # self.layer.set_weight_map_form_file("./data/hnn/weight_pos_100_100_chip_8_.npz")
        self.layer.set_weight_map_form_file("./data/hnn/weight_pos_100_100_chip_6_.npz")
        compensation_para:dict={
            "value":0.65,
            "real_mean":550,
            "odd_offset":2,
            "even_offset":4,
            "odd_mult":1,
            "even_mult":1,
            "all_mult":1,
            "add_wire":True
        }

        self.layer.set_forward_paramater(forward_type=2,interval=18,compensation_para=compensation_para)

    def get_origin(self):
        """
            获取损害后的图片
        """
        return self.processed_patterns


    def damage_pattern(self,pattern, damage_rate):
        """
            损坏图片
        """
        damaged = pattern.copy().flatten()
        N = damaged.size
        num_flip = int(damage_rate * N)
        flip_indices = np.random.choice(N, num_flip, replace=False)
        damaged[flip_indices] *= -1
        return damaged.reshape((self.side, self.side))

    def get_damaged(self,damage_rate=0.15):
        """
            获取损坏后的图片
        """
        self.damaged_patterns = []
        for p in self.processed_patterns:
            damaged = self.damage_pattern(p, damage_rate)
            self.damaged_patterns.append(damaged)
        return self.damaged_patterns
