from modules import ADC,DAC,CHIP
from network.writeConfig import WriteConfig
import numpy as np

class Layer():
    chip = None                         # 芯片模块
    # -------------------------------------------------------------权重配置
    weight_target = None                # 目标权重
    weight_real = None                  # 实际读到的权重
    cond_real = None                    # 实际电导

    min_cond = 200                      # 最低电导
    max_cond = 1000                     # 最高电导
    min_weight = None                   # 权重最小值
    max_weight = None                   # 权重最大值

    weight_map = None                   # 权重映射结果
    weight_diff = True                  # 差分器件
    weight_transpose = True             # 转置权重
    pos = None                          # 权重位置，左上角位置和右下角位置
    # -------------------------------------------------------------推理配置

    def __init__(self,chip:CHIP):
        """
        Args:
            chip:芯片模块,通过调用这个模块读写权重和推理
            weight_diff:是否使用差分器件表示权重
            transpose:是否转置权重
        """
        self.chip = chip

    def set_weight(self,weight:np.ndarray,min_weight,max_weight,pos:tuple[int,int,int,int],weight_diff:bool = True):
        """
        Args:
            weight:设置目标权重权重
            pos:权重位置，左上角位置(和是否转置无关的位置)和右下角位置(和是否转置无关的位置)

            默认会进行转置
        """
        # 左闭右开区间
        self.weight_diff = weight_diff
        self.weight_target = weight.copy().T
        self.pos = pos
        self.min_weight = min_weight
        self.max_weight = max_weight

    def weight_setting(self,min_cond=200,max_cond=1000):
        self.min_cond = min_cond
        self.max_cond = max_cond

    # """
    # 差分器件写权重：
    #     1. 先把一个器件的权重写到尽可能接近目标值的地方,多次写之后,再调整另一个差分器件,结束
    #     2. 写一个器件一次,再写另一个器件一次,循环往复
    #     3. 写一个器件5次,再写另一个器件5次,循环往复
    #     4. 一直set到目标点
    # """
    def write_weight(self,write_config:WriteConfig,loop_times = 10,write_verify_time = 10,threshold = 25,reset = False):
        pos = self.pos
        need_write = np.zeros((256,256),dtype=bool)
        target_cond = np.zeros((256,256))
        weight_cond = self.weight_to_cond(self.weight_target)
        if reset:
            self.reset_pos(pos,write_config)
        if self.weight_diff:
            for i in range(loop_times):
                cond_neg = self.cond_to_diff_cond(self.read_cond_point(pos,write_config.from_row),num=1)
                target_cond = self.get_write_target_cond(target_cond,pos,weight_cond+cond_neg,0)
                need_write = self.get_write_addr(need_write,pos,0) & (target_cond>0)
                target_cond.clip(100, 1200, out=target_cond)
                self.write_verify(write_time=int(write_verify_time/2),need_read=need_write,target_cond=target_cond,threshold=threshold,write_config=write_config)

                cond_pos = self.cond_to_diff_cond(self.read_cond_point(pos,write_config.from_row),num=0)
                target_cond = self.get_write_target_cond(target_cond,pos,cond_pos-weight_cond,1)
                need_write = self.get_write_addr(need_write,pos,1) & (target_cond>0)
                target_cond.clip(100,1200,out=target_cond)
                self.write_verify(write_time=int(write_verify_time/2),need_read=need_write,target_cond=target_cond,threshold=threshold,write_config=write_config)

    def write_weight2(self,write_config:WriteConfig,write_verify_time = 10,threshold = 25,reset = False):
        """
            正负权重分开写
        """
        pos = self.pos
        need_write = np.zeros((256,256),dtype=bool)
        target_cond = np.zeros((256,256))
        weight_cond = self.weight_to_cond(self.weight_target)
        if reset:
            self.reset_pos(pos,write_config)
        if self.weight_diff:
            read_weight = self.read_cond_point(pos,write_config.from_row)
            # 先只写正权重
            weight_cond_pos = weight_cond.copy()
            weight_cond_pos[weight_cond_pos<0] = -10000

            cond_neg = self.cond_to_diff_cond(read_weight,num=1)
            target_cond = self.get_write_target_cond(target_cond,pos,weight_cond_pos+cond_neg,0)
            # 
            need_write = self.get_write_addr(need_write,pos,0) & (target_cond>0)
            target_cond.clip(50, 1200, out=target_cond)
            self.write_verify(write_time=int(write_verify_time),need_read=need_write,target_cond=target_cond,threshold=threshold,write_config=write_config)


            # 再只写负权重
            weight_cond_neg = weight_cond.copy()
            weight_cond_neg[weight_cond_neg>0] = 10000

            cond_pos = self.cond_to_diff_cond(read_weight,num=0)
            target_cond = self.get_write_target_cond(target_cond,pos,cond_pos-weight_cond_neg,1)

            need_write = self.get_write_addr(need_write,pos,1) & (target_cond>0)
            target_cond.clip(50,1200,out=target_cond)
            self.write_verify(write_time=int(write_verify_time),need_read=need_write,target_cond=target_cond,threshold=threshold,write_config=write_config)


    def reset_pos(self,pos,write_config:WriteConfig):
        chip = self.chip
        row,col = chip.setting.chip_latch_num,chip.setting.chip_latch_num
        # 先把要写权重的地方reset掉
        need_write = np.zeros((row,col))
        need_write[pos[0]:pos[1],pos[2]:pos[3]] = 1
        self.chip.write_point2(crossbar=need_write,
                               write_voltage=write_config.reset_voltage,tg=write_config.reset_tg,pulse_width=write_config.reset_pulse_width,
                               set_device=False)

    def read_cond_point(self,pos,from_row):
        """
            读出一块的权重值
        """
        chip = self.chip
        x1,x2,y1,y2 = pos

        voltage_base = chip.read_point3(x1,x2,y1,y2,read_voltage=0,tg=5,gain=1,from_row=from_row,out_type=0)
        voltage = chip.read_point3(x1,x2,y1,y2,read_voltage=0.1,tg=5,gain=1,from_row=from_row,out_type=0)
        res = chip.voltage_to_cond(voltage-voltage_base)
        return res

    def write_verify(self,write_time,need_read,target_cond,threshold,write_config:WriteConfig):
        chip = self.chip
        tg_v=(target_cond-write_config.intercept)/write_config.slope
        for i in range(write_time):
            print(f"写验证{i}")
            voltage_base = chip.read_point2(crossbar=need_read,read_voltage=0,tg=5,gain=1,from_row=write_config.from_row,out_type=0)
            voltage = chip.read_point2(crossbar=need_read,read_voltage=0.1,tg=5,gain=1,from_row=write_config.from_row,out_type=0)
            cond_sub_base = chip.voltage_to_cond(voltage-voltage_base)

            condition_reset = ((cond_sub_base > (target_cond+threshold)))&need_read
            condition_set = ((cond_sub_base < (target_cond-threshold)))&need_read
            
            if i>0:
                if i<3:
                    tg_v[condition_reset] -= 0.08
                    tg_v[condition_set] += 0.08
                elif i<6:
                    tg_v[condition_reset] -= 0.04
                    tg_v[condition_set] += 0.04
                else:
                    tg_v[condition_reset] -= 0.02
                    tg_v[condition_set] += 0.02

                tg_v.clip(0, 5, out=tg_v)

            # reset的点
            chip.write_point2(crossbar=condition_reset,write_voltage=write_config.reset_voltage,tg=write_config.reset_tg,pulse_width=write_config.reset_pulse_width,set_device=False)
            chip.write_point2(crossbar=condition_reset,write_voltage=write_config.set_voltage,tg=tg_v,pulse_width=write_config.set_pulse_width,set_device=True)

            # set的点
            chip.write_point2(crossbar=condition_set,write_voltage=write_config.set_voltage,tg=tg_v,pulse_width=write_config.set_pulse_width,set_device=True)

        return tg_v
    def cond_to_diff_cond(self,cond,num):
        """
            对应区域的差分电导转成差分对中的正电导或负电导
        """
        return cond[num::2,:]
    
    def diff_cond_to_cond(self,cond):
        """
            差分电导转成减去之后的值
        """
        even_columns = cond[::2,:]  # 从第0行开始，间隔2
        odd_columns = cond[1::2,:]  # 从第1行开始，间隔2
        cond = even_columns - odd_columns
        return cond

    def get_write_addr(self,crossbar,pos,num):
        """
            返回差分权重的写地址
        """
        x1,x2,y1,y2 = pos
        crossbar[:]=False
        crossbar[(x1+num):x2:2,y1:y2] = True
        return crossbar
    
    def get_write_target_cond(self,crossbar,pos,cond,num):
        """
            返回差分权重
        """
        x1,x2,y1,y2 = pos
        crossbar[:]=0
        crossbar[(x1+num):x2:2,y1:y2] = cond
        return crossbar


    def weight_to_cond(self,weight):
        """
            返回权重对应的电导,差分是最终的电导差值,非差分是实际单个器件的电导值
        """
        if self.weight_diff:
            # 权重映射电导范围从-(max_cond-min_cond)到（max_cond-min_cond)，总范围大小（max_cond-min_cond）*2
            cond = weight/self.max_weight*(self.max_cond-self.min_cond)
        else:
            # 权重映射电导范围从min_cond到max_cond,总范围大小max_cond-min_cond
            cond = (weight - self.min_weight)/(self.max_weight-self.min_weight)*(self.max_cond-self.min_cond)+self.min_cond
        
        return cond
    
    def cond_to_weight(self,cond):
        if self.weight_diff:
            return cond/(self.max_cond-self.min_cond)*self.max_weight

    def forward(self,state_flat:np.ndarray):
        """
            state_flat:为1*100的np数组
            split_type = 0,就是采用
        """
        x1,x2,y1,y2 = self.pos
        # 先处理正输入
        col_index = np.where(state_flat > 0)[1]+y1
        col_index = col_index.tolist()
        if col_index:
            v_base = self.chip.read_chunk_parallel2(x1,x2,y1,y2,row_index=None,col_index=[col_index],read_voltage=0,tg=5,gain=3,
                                                from_row=not self.weight_transpose,out_type=0,compute=True)
            v_pos = self.chip.read_chunk_parallel2(x1,x2,y1,y2,row_index=None,col_index=[col_index],read_voltage=0.1,tg=5,gain=3,
                                                        from_row=not self.weight_transpose,out_type=0,compute=True)
            # 返回的是200*1的np数组
            v_cond_pos = self.chip.voltage_to_cond(v_pos-v_base)

        else:
            v_cond_pos = np.zeros((y2-y1,1))
        
        # 再处理负输入
        col_index = np.where(state_flat < 0)[1]+y1
        col_index = col_index.tolist()
        if col_index:
            v_base = self.chip.read_chunk_parallel2(x1,x2,y1,y2,row_index=None,col_index=[col_index],read_voltage=0,tg=5,gain=3,
                                        from_row=not self.weight_transpose,out_type=0,compute=True)
            v_neg = self.chip.read_chunk_parallel2(x1,x2,y1,y2,row_index=None,col_index=[col_index],read_voltage=0.1,tg=5,gain=3,
                                                        from_row=not self.weight_transpose,out_type=0,compute=True)
            v_cond_neg = self.chip.voltage_to_cond(v_neg-v_base)
        else:
            v_cond_neg = np.zeros_like(v_cond_pos)
        v_cond = v_cond_pos - v_cond_neg
        v_cond = self.diff_cond_to_cond(v_cond)
        
        return self.cond_to_weight(v_cond)



