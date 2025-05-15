import math
import scipy.io as sio
import numpy as np

# 存储的svm权重位置
svm_weight_pos = np.load("./data/svm/svm_weight_pos.npz")
good_device = [np.array(svm_weight_pos["row"]),np.array(svm_weight_pos["col"])]
# 用于线组补偿的参数
r_out = np.load("./data/chip_1_4_col_r_out.npy")
r_w = np.load("./data/chip_1_4_col_r_wire.npy")
# 电导和权重映射的范围
cond_min,cond_max,cond_reference = 0,1100,550
cond_range = cond_max-cond_reference
weight_min,weight_max = -0.17,0.17



# svm推理用到的数据，输入x和对应的y标签
mat_contents = sio.loadmat('./data/svm/train3.mat')  # 替换为实际文件路径
data = mat_contents['train_3']  # 根据实际文件中的变量名调整

X = data[:, :128]  # 特征矩阵，尺寸为 (N, d) 其中 d=128
y = data[:, 128].flatten()  # 标签向量，尺寸为 (N, )
y = y - 1
ones_column = np.ones((15000, 1),dtype=int)

X_NEW = np.concatenate((X, ones_column), axis=1)




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
            Args:
                row_index是需要开的行号[0,255]列表
                col_index是输出的列好[0,255]列表
                forward_type:
                    =1 表示并行列输出
                    =2 表示逐列输出
                    =3 逐点读然后计算推理结果
                value用于补偿的一个参数
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
            # 为了更好的推理效果，可以减去base
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
            # 为了更好的推理效果，可以减去base
            need_read = np.zeros((256,256),dtype=bool)
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
            need_read = np.zeros((256,256),dtype=bool)
            weight_pos = np.ix_(row_index, col_index)
            need_read[weight_pos] = True
            voltage_base = chip.read_point2(crossbar=need_read,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
            voltage = chip.read_point2(crossbar=need_read,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
            cond = chip.voltage_to_cond(voltage=voltage-voltage_base)[weight_pos]

            # 单位A
            real_i =np.sum(cond,axis=0) - cond_reference*row_nums
            real_value = real_i/(cond_range)*weight_max
            return real_value.flatten()

    def forward_from_row(self,chip,x,row_index,col_index,interval = 60,forward_type = 2,value=0.875):
        """
            Args:
                x表示神经网络输入的向量
                row_index表示存储权重矩阵的行号
                col_index表示存储权重矩阵的列号
                interval表示每次最多开多少行进行推理
                forward_type:
                    =1 表示并行列输出
                    =2 表示逐列输出
                    =3 逐点读然后计算推理结果
                value用于补偿结果的一个参数
        """
        y = np.zeros((len(col_index)))
        x = x.flatten()

        # 因为svm输入只有0，1，2
        # 为2的输入进行推理一次
        row = row_index[np.where(x > 1.5)]
        row_nums = len(row)
        steps = math.ceil(row_nums/interval)
        if row_nums>0:
            for i in range(steps):
                y += self.forward_unsigned_from_row(chip,row[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type,value=value)
        
        # 为1的输入进程推理一次
        row =row_index[np.where(x > 0.5)]
        row_nums = len(row)
        if row_nums>0:
            steps = math.ceil(row_nums/interval)
            for i in range(steps):
                y += self.forward_unsigned_from_row(chip,row[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type,value=value)

        # 这里没有负数输入，有负数输入，负输入进行推理，然后减去即可
        return y

    def forward(self,chip):
        # 推理结果
        scores_all = np.zeros((self.select_num,5))

        # self.select_num个推理样本
        for i in range(self.select_num):
            scores_all[i,:]=self.forward_from_row(chip,self.X_SELECT[i,:],good_device[0],good_device[1],interval=60,forward_type=2,value=0.875)
        # 得到对应的推理结果
        y_pred = np.argmax(scores_all, axis=1)
        return y_pred
