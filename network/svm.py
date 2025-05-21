import math
import scipy.io as sio
import numpy as np

# from layer import svmLayer
from network import svmLayer


class svm():

    def __init__(self,chip):
        """
            加载数据集,进行预处理
        """
        data = np.load("./data/svm/data2.npz")
        self.select_num = 100
        self.x = data["x"]
        self.y = data["y"]

        # Wb=np.load('../data/svm/svm_weight_90.npy').T
        # print(np.min(Wb),np.max(Wb))
        self.layer=svmLayer(chip=chip,weight_target=0,weight_min=-4.5,weight_max=4.5,cond_min=0,cond_max=1100,cond_reference=550)
        # self.layer.set_weight_map_form_file("./data/svm/weight_pos_128_5_chip_8_.npz")
        self.layer.set_weight_map_form_file("./data/svm/weight_pos_128_5_chip_6_.npz")
        compensation_para:dict={
            "compensation_type":0,
            "value":0.7,
            "real_mean":550,
            "odd_offset":0,
            "even_offset":0,
            "odd_mult":1,
            "even_mult":1,
            "all_mult":1,
            "add_wire":True
        }
        self.layer.set_forward_paramater(forward_type=2,interval=60,compensation_para=compensation_para)

    def get_correct_labels(self):
        return self.y

    def forward(self):
        # 推理结果
        scores_all = np.zeros((self.select_num,5))

        # self.select_num个推理样本
        for i in range(self.select_num):
            scores_all[i,:]=self.layer.forward_from_row(self.x[i])
        # 得到对应的推理结果
        y_pred = np.argmax(scores_all, axis=1)
        return y_pred
