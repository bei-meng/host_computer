import math
import numpy as np

good_device = np.load("./data/good_point_100_100_1_4.npy")
r_out = np.load("./data/chip_1_4_col_r_out.npy")
r_w = np.load("./data/chip_1_4_col_r_wire.npy")
cond_min,cond_max,cond_reference = 0,1100,550
cond_range = cond_max-cond_reference
weight_min,weight_max = -0.17,0.17

class hnn():
    net_size = 100  # 例如 100 表示 10×10
    num_imgs = 5
    side = int(np.sqrt(net_size))  # 图像边长
    threshold = 128
    selected_patterns = None
    processed_patterns = None
    damaged_patterns = None

    def __init__(self):
        """
            加载数据集,进行预处理
        """
        self.processed_patterns = np.load("./data/hnn/processed_patterns.npy")

    def get_origin(self):
        """
            获取损害后的图片
        """
        return self.processed_patterns


    def damage_pattern(self,pattern, damage_rate=0.1):
        """
            损坏图片
        """
        damaged = pattern.copy().flatten()
        N = damaged.size
        num_flip = int(damage_rate * N)
        flip_indices = np.random.choice(N, num_flip, replace=False)
        damaged[flip_indices] *= -1
        return damaged.reshape((self.side, self.side))

    def get_damaged(self,damage_rate=0.1):
        """
            获取损害后的图片
        """
        self.damaged_patterns = []
        for p in self.processed_patterns:
            damaged = self.damage_pattern(p, damage_rate)
            self.damaged_patterns.append(damaged)
        return self.damaged_patterns


    def forward_unsigned_from_row(self,chip,row_index,col_index,forward_type=2):
        """
            从行给信号进行推理
        """
        col_nums = len(col_index)
        row_nums = len(row_index)
        from_row = True
        if col_nums <= 0:
            return np.zeros((len(row_index),1))
        
        min_row,max_row = np.min(row_index),np.max(row_index)
        row_rw = np.array([(256-max_row)*r_w[i] if i%2==0 else (min_row)*r_w[i] for i in col_index])
        gain = 1 if row_nums<=10 else 3
        if forward_type==1:
            # -------------------------------------
            voltage_base = chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],
                                                        read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0,compute=True
                                                    # ,tia_split=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3]
                                                    ,tia_split=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,]
                                                    # ,tia_split=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
                                                    )
            voltage = chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],
                                                read_voltage=0.1,tg=5,gain=gain, from_row=from_row,out_type=0,compute=True
                                                # ,tia_split=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3]
                                                ,tia_split=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,]
                                                # ,tia_split=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
                                                )
            parallel_r = chip.voltage_to_resistance(voltage = voltage-voltage_base)[:,col_index]*1e3 - r_out[col_index] - row_rw - r_w[col_index]*(row_nums**0.875)
            # 单位A
            parallel_i = 1/parallel_r - cond_reference*1e-6*row_nums
            parallel_value = parallel_i/(cond_range*1e-6)*weight_max
            return parallel_value.flatten()
        elif forward_type==2:
            need_read = np.zeros((256,256),dtype=bool)
            weight_pos = np.ix_(row_index, col_index)
            need_read[weight_pos] = True

            voltage_base=chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
            voltage=chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
            not_parallel_r = chip.voltage_to_resistance(voltage = voltage-voltage_base)[:,col_index]*1e3 - r_out[col_index] - row_rw - r_w[col_index]*(row_nums**0.875)
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
    

    def forward_from_row(self,chip,state_flat:np.ndarray,interval=50,forward_type=2):
        """
            state_flat:为1*100的np数组
            split_type = 0,就是采用
        """
        state_flat_new = state_flat.reshape(1,100)

        col_index = good_device[1]
        
        row_index = good_device[0][np.where(state_flat_new > 0)[1]]
        row_nums = len(row_index)
        steps = math.ceil(row_nums/interval)
        value_pos = np.zeros((len(col_index)))
        for i in range(steps):
            value_pos += self.forward_unsigned_from_row(chip,row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type)
        

        row_index = good_device[0][np.where(state_flat_new < 0)[1]]
        row_nums = len(row_index)
        steps = math.ceil(row_nums/interval)
        value_neg = np.zeros((len(col_index)))
        for i in range(steps):
            value_neg += self.forward_unsigned_from_row(chip,row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=forward_type)

        return value_pos-value_neg
