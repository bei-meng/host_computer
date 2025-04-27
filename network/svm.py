import math
import scipy.io as sio
import numpy as np

svm_weight_pos = np.load("./data/svm/svm_weight_pos.npz")
good_device = [np.array(svm_weight_pos["row"]),np.array(svm_weight_pos["col"])]
r_out = np.load("./data/chip_1_4_col_r_out.npy")
r_w = np.load("./data/chip_1_4_col_r_wire.npy")


mat_contents = sio.loadmat('./data/svm/train3.mat')  # 替换为实际文件路径
data = mat_contents['train_3']  # 根据实际文件中的变量名调整

X = data[:, :128]  # 特征矩阵，尺寸为 (N, d) 其中 d=128
y = data[:, 128].flatten()  # 标签向量，尺寸为 (N, )
# 为方便运算，将标签调整到 0~K-1 （K=5）
y = y - 1
ones_column = np.ones((15000, 1),dtype=int)

# 使用np.concatenate函数将这一列添加到原始矩阵的最后
X_NEW = np.concatenate((X, ones_column), axis=1)


cond_min,cond_max,cond_reference = 0,1100,550
cond_range = cond_max-cond_reference
weight_min,weight_max = -0.17,0.17


need_read = np.zeros((256,256),dtype=bool)


class svm():
    X_SELECT = None
    Y_SELECT = None
    select_num = None

    def __init__(self):
        """
            加载数据集,进行预处理
        """
        rows_to_select=np.load("./data/svm/correct_data.npy")[:100]
        self.select_num = len(rows_to_select)
        self.X_SELECT = X_NEW[rows_to_select, :]
        self.Y_SELECT = y[rows_to_select]

    def get_correct_labels(self):
        return self.Y_SELECT


    def forward_unsigned_from_row(self,chip,row_index,col_index,forward_type=2,value=0.875):
        """
            从行给信号进行推理
        """
        col_nums,row_nums = len(col_index),len(row_index)
        from_row = True
        if col_nums <= 0:
            return np.zeros((len(row_index),1))
        
        min_row,max_row = np.min(row_index),np.max(row_index)
        row_rw = np.array([(256-max_row)*r_w[i] if i%2==0 else (min_row)*r_w[i] for i in col_index])
        gain = 1 if row_nums<=10 else 3
        if forward_type==1:
            # -------------------------------------
            # voltage_base = chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],
            #                                             read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0,compute=True
            #                                         # ,tia_split=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3]
            #                                         # ,tia_split=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,]
            #                                         # ,tia_split=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
            #                                         )
            voltage = chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],
                                                read_voltage=0.1,tg=5,gain=gain, from_row=from_row,out_type=0,compute=True
                                                # ,tia_split=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3]
                                                # ,tia_split=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,]
                                                # ,tia_split=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
                                                )
            parallel_r = chip.voltage_to_resistance(voltage = voltage)[:,col_index]*1e3 - r_out[col_index] - row_rw - r_w[col_index]*(row_nums**value)
            # 单位A
            parallel_i = 1/parallel_r - cond_reference*1e-6*row_nums
            parallel_value = parallel_i/(cond_range*1e-6)*weight_max
            return parallel_value.flatten()
        elif forward_type==2:
            need_read[:]=False
            weight_pos = np.ix_(row_index, col_index)
            need_read[weight_pos] = True

            # voltage_base=chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
            voltage=chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
            not_parallel_r = chip.voltage_to_resistance(voltage = voltage)[:,col_index]*1e3 - r_out[col_index] - row_rw - r_w[col_index]*(row_nums**value)
            # 单位A
            not_parallel_i = 1/not_parallel_r - cond_reference*1e-6*row_nums
            not_parallel_value = not_parallel_i/(cond_range*1e-6)*weight_max
            return not_parallel_value.flatten()
        elif forward_type==3:
            need_read[:]=False
            weight_pos = np.ix_(row_index, col_index)
            need_read[weight_pos] = True
            voltage_base = chip.read_point2(crossbar=need_read,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
            voltage = chip.read_point2(crossbar=need_read,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
            cond = chip.voltage_to_cond(voltage=voltage-voltage_base)[weight_pos]

            # 单位A
            real_i =np.sum(cond,axis=0) - cond_reference*row_nums
            real_value = real_i/(cond_range)*weight_max
            return real_value.flatten()

    # def forward_from_row(self,chip,state_flat:np.ndarray,interval=50,forward_type=2):
    def forward_from_row(self,chip,x:np.ndarray,interval = 60,forward_type = 2,value=0.875):
        """
            x只有3个值,0,1,2
            单列输出用0.785
        """
        col_index = good_device[1]
        y = np.zeros((len(col_index)))
        x = x.flatten()

        row_index = good_device[0][np.where(x > 1.5)]
        row_nums = len(row_index)
        steps = math.ceil(row_nums/interval)
        if row_nums>0:
            for i in range(steps):
                y += self.forward_unsigned_from_row(chip,row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type,value=value)
        
        row_index = good_device[0][np.where(x > 0.5)]
        row_nums = len(row_index)
        if row_nums>0:
            steps = math.ceil(row_nums/interval)
            for i in range(steps):
                y += self.forward_unsigned_from_row(chip,row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type,value=value)

        return y

    def forward(self,chip):
        scores_all = np.zeros((self.select_num,5))

        for i in range(self.select_num):
            scores_all[i,:]=self.forward_from_row(chip,self.X_SELECT[i,:],interval=60,forward_type=2,value=0.875)

        y_pred = np.argmax(scores_all, axis=1)
        return y_pred
