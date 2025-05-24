import numpy as np
import math
from modules import CHIP
class Layer():
    chip = None

    weight_target=None              # 目标权重
    weight_real=None                # 器件真实权重

    map_cond = None                 # 映射的电导,已经加过reference

    cond_min = None                 # 使用的最小电导
    cond_max = None                 # 使用的最大电导
    cond_reference = None           # 参考电导，0值
    cond_range = None               # 电导上下范围
    weight_min = None               # 最小权重
    weight_max = None               # 最大权重

    row_index = None                # 权重映射的行号
    col_index = None                # 权重映射的列号

    # tia_split=[0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3]
    tia_split=[0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,]
    # tia_split=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,]
    from_row = True

    chip:CHIP = None

    row_nums_threshold = 30

    # 推理相关参数
    compensation_para:dict={
        "value":0.875,
        "real_mean":550,
        "odd_offset":0,
        "even_offset":0,
        "odd_mult":1,
        "even_mult":1,
        "all_mult":1,
        "add_wire":True
    }
    interval = 25
    forward_type = 2


    need_read = np.zeros((256,256),dtype=bool)

    bad_point = None

    def __init__(self,chip:CHIP,weight_target,weight_min=-1,weight_max=1,cond_min=0,cond_max=1100,cond_reference=550):
        """
            初始化权重的参数
        """
        self.chip:CHIP = chip
        self.cond_min = cond_min
        self.cond_max = cond_max
        self.cond_reference = cond_reference
        self.cond_range = cond_max-cond_reference

        self.map_cond = weight_target/weight_max*self.cond_range
        self.weight_min = weight_min
        self.weight_max = weight_max
        self.weight_target = weight_target

    def save_weight(self,path):
        """
            存储权重
        """
        np.save(path,self.read_cond_point())

    def set_forward_paramater(self,forward_type,interval,compensation_para):
        self.forward_type=  forward_type
        self.interval = interval
        self.compensation_para = compensation_para
    

    def set_weight_map_form_file(self,filename):
        """
            从文件中加载权重映射
        """
        weight_pos = np.load(filename)
        self.set_weight_map(np.array(weight_pos["row"]),np.array(weight_pos["col"]))


    def set_weight_map(self,row_index,col_index):
        """
            设置权重的行列号映射
        """
        self.row_index = row_index
        self.col_index = col_index


    def get_weight_pos(self):
        """
            获取权重的映射位置
        """
        return np.ix_(self.row_index, self.col_index)
    
    def get_target_cond(self):
        """
            获取实际写的电导大小
        """
        return self.map_cond + self.cond_reference


    def calculate_value_from_r(self,resistence,nums):
        """
            将计算出来的电阻,单位Ω
            nums:输入的行数/列数
        """
        parallel_i = 1/resistence - self.cond_reference*1e-6*nums
        parallel_value = parallel_i/(self.cond_range*1e-6)*self.weight_max
        return parallel_value.flatten()
    
    def calculate_value_from_c(self,cond,nums):
        """
            将计算出来的电阻,单位us
            nums:输入的行数/列数
        """
        real_i =np.sum(cond,axis=0) - self.cond_reference*nums
        real_value = real_i/(self.cond_range)*self.weight_max
        return real_value.flatten()
    

    def read_cond_point(self,from_row=True):
        self.need_read[:]=False
        weight_pos = np.ix_(self.row_index, self.col_index)
        self.need_read[weight_pos] = True

        voltage_base = self.chip.read_point2(crossbar=self.need_read,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
        voltage = self.chip.read_point2(crossbar=self.need_read,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
        resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base)
        cond = self.chip.compensation.compensation_point(resistence=resistence,from_row=from_row,return_type=0)
        return cond[weight_pos]
    
    def read_weight_point(self,from_row=True):
        """
            读出真实权重
        """
        cond = self.read_cond_point(from_row)
        weight = (cond-self.cond_reference)/self.cond_range*self.weight_max
        self.weight_real = weight
        return weight
    
    def forward_unsigned_from_row(self,row_index,col_index,forward_type,return_type=0,compensation_para:dict={
                                 "value":0.875,
                                 "real_mean":550,
                                 "odd_offset":0,
                                 "even_offset":0,
                                 "odd_mult":1,
                                 "even_mult":1,
                                 "all_mult":1,
                                 "add_wire":True
                                 }):
        """
            Args:
                row_index输入的行/列号
                col_index输出的行/列号
                forward_type:
                    =1 表示并行列输出
                    =2 表示逐列输出
                    =3 逐点读然后计算推理结果
        """
        from_row = True
        col_nums,row_nums = len(col_index),len(row_index)
        
        gain = 1 if row_nums<=self.row_nums_threshold else 3
        if forward_type==1:
            voltage_base = self.chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0,compute=True,tia_split=self.tia_split)
            voltage = self.chip.read_chunk_parallel2(row_index=[row_index],col_index=[col_index],read_voltage=0.1,tg=5,gain=gain, from_row=from_row,out_type=0,compute=True,tia_split=self.tia_split)
            resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base).flatten()
            resistence = self.chip.compensation.compensation_forward(row_index,resistence,from_row,compensation_para=compensation_para,return_type=2)[col_index]
            if return_type==0:
                return self.calculate_value_from_r(resistence=resistence,nums=row_nums)
            else:
                return 1/resistence*1e6
        elif forward_type==2:
            self.need_read[:]=False
            weight_pos = np.ix_(row_index, col_index)
            self.need_read[weight_pos] = True
            if self.bad_point is not None:
                self.need_read[self.bad_point] = False

            voltage_base=self.chip.compute(crossbar=self.need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
            voltage=self.chip.compute(crossbar=self.need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
            resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base).flatten()
            resistence = self.chip.compensation.compensation_forward(row_index,resistence,from_row,compensation_para=compensation_para,return_type=2)[col_index]
            if return_type==0:
                return self.calculate_value_from_r(resistence=resistence,nums=row_nums)
            else:
                return 1/resistence*1e6
            
        elif forward_type==3:
            self.need_read[:]=False
            weight_pos = np.ix_(row_index, col_index)
            self.need_read[weight_pos] = True

            voltage_base = self.chip.read_point2(crossbar=self.need_read,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
            voltage = self.chip.read_point2(crossbar=self.need_read,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
            resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base)
            cond = self.chip.compensation.compensation_point(resistence,from_row,return_type=0)[weight_pos]
            if return_type==0:
                return self.calculate_value_from_c(cond=cond,nums=row_nums) 
            else:
                return np.sum(cond,axis=0)

    def calculate_error_from_row(self,row_index,col_index,compensation_para):
        """
            Args:
                row_index输入的行/列号
                col_index输出的行/列号
                forward_type:
                    =1 表示并行列输出
                    =2 表示逐列输出
                    =3 逐点读然后计算推理结果
        """
        from_row = True
        col_nums,row_nums = len(col_index),len(row_index)
        ans = np.zeros((row_nums,4))

        #-------------------------------------逐点读数据
        self.need_read[:]=False
        weight_pos = np.ix_(row_index, col_index)
        self.need_read[weight_pos] = True

        voltage_base = self.chip.read_point2(crossbar=self.need_read,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
        voltage = self.chip.read_point2(crossbar=self.need_read,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
        resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base)
        cond0 = self.chip.compensation.compensation_point(resistence,from_row,return_type=0)[weight_pos]
        for i in range(row_nums):
            ans[i,0]=np.sum(cond0[:i+1,0])

        #-------------------------------------并行
        for i in range(row_nums):
            gain = 1 if i<=10 else 3
            self.need_read[:]=False
            weight_pos = np.ix_(row_index[:i+1], col_index)
            self.need_read[weight_pos] = True

            voltage_base=self.chip.compute(crossbar=self.need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
            voltage=self.chip.compute(crossbar=self.need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
            resistence = self.chip.voltage_to_resistance(voltage = voltage-voltage_base).flatten()
            ans[i,1]=(1/resistence*1e3)[col_index]
            old = compensation_para["add_wire"]
            compensation_para["add_wire"]=False
            resistence1 = self.chip.compensation.compensation_forward(row_index,resistence,from_row,return_type=2,compensation_para=compensation_para)[col_index]
            ans[i,2]=(1/resistence1*1e6)[0]
            compensation_para["add_wire"]=old
            resistence2 = self.chip.compensation.compensation_forward(row_index,resistence,from_row,return_type=2,compensation_para=compensation_para)[col_index]
            ans[i,3]=(1/resistence2*1e6)[0]
        return ans
        


class hnnLayer(Layer):
    
    def forward_from_row(self,x:np.ndarray):
        """
            x为输入,会转换为一维数组
        """
        x = x.reshape(1,-1)
        interval = self.interval
        col_index = self.col_index


        value_pos = np.zeros((len(col_index)))
        value_neg = np.zeros((len(col_index)))
        
        row_index = self.row_index[np.where(x > 0)[1]]
        row_nums = len(row_index)
        if row_nums>0:
            steps = math.ceil(row_nums/interval)
            for i in range(steps):
                value_pos += self.forward_unsigned_from_row(row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=self.forward_type,compensation_para=self.compensation_para)
        

        row_index = self.row_index[np.where(x < 0)[1]]
        row_nums = len(row_index)
        if row_nums>0:
            steps = math.ceil(row_nums/interval)
            for i in range(steps):
                value_neg += self.forward_unsigned_from_row(row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=self.forward_type,compensation_para=self.compensation_para)

        return value_pos-value_neg
    

class svmLayer(Layer):
    def forward_from_row(self,x):
        """
            x只有3个值,0,1,2
            单列输出用0.785
        """
        interval = self.interval
        col_index = self.col_index

        y = np.zeros((len(col_index)))
        x = x.flatten()
        
        row_index = self.row_index[np.where(x > 1.5)]
        row_nums = len(row_index)
        steps = math.ceil(row_nums/interval)
        if row_nums>0:
            for i in range(steps):
                y += self.forward_unsigned_from_row(row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=self.forward_type,compensation_para=self.compensation_para)
        

        row_index = self.row_index[np.where(x > 0.5)]
        row_nums = len(row_index)
        if row_nums>0:
            steps = math.ceil(row_nums/interval)
            for i in range(steps):
                y += self.forward_unsigned_from_row(row_index[i*interval:min((i+1)*interval,row_nums)],col_index,forward_type=self.forward_type,compensation_para=self.compensation_para)

        return y