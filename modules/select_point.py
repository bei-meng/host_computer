import numpy as np
import random


class SELECT():
    good_point = np.zeros((256,256))

    def init_point(self,reset_path,set_path,value_stack_off=0.2,value_stack_on=-0.2):
        """
            初始化好点
        """
        reset_path = np.load(reset_path)
        set_path = np.load(set_path)
        self.good_point = (reset_path&set_path).astype(int) + (~set_path).astype(int)*value_stack_off + (~reset_path).astype(int)*value_stack_on

    def add_used(self,path):
        """
            增加使用过的点
        """
        weight_pos = np.load(path)
        pos = np.ix_(np.array(weight_pos["row"]), np.array(weight_pos["col"]))
        self.good_point[pos]=-65535

    def Reset(self,chip,need_read,write_times,start_v,delta_v,tg,threshold,reset_pulse_width,read_type=2,sub_base=False,vmax=1000,plot_cond=None):
        voltage_base = np.zeros((256,256))
        voltage = np.zeros((256,256))
        cond_sub_base = None
        for i in range(write_times):
            print(f"write_time = {i}")
            v = start_v+i*delta_v
            if read_type == 2:
                if sub_base:
                    voltage_base[need_read] = chip.read_point2(crossbar=need_read, read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)[need_read]
                voltage[need_read] = chip.read_point2(crossbar=need_read, read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)[need_read]
            elif read_type == 3:
                pos = (0,256,0,256)
                if sub_base:
                    voltage_base = chip.read_point3(*pos,read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
                voltage = chip.read_point3(*pos,read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
            if sub_base:
                cond_sub_base = chip.voltage_to_cond(voltage-voltage_base)
            else:
                cond_sub_base = chip.voltage_to_cond(voltage)

            condition_reset = (cond_sub_base>threshold)&need_read
            need_read = condition_reset
            if plot_cond:
                plot_cond(cond_sub_base,title=f"v={v:.2f}-needReset={np.sum(condition_reset)}",vmax=vmax)

            chip.write_point2(crossbar=condition_reset,write_voltage=v,tg=tg,pulse_width=reset_pulse_width,set_device=False)

    def Forming(self,chip,need_read,write_times,write_voltage,start_tg,delta_tg,threshold,set_pulse_width,read_type=2,sub_base=False,plot_cond=None):
        voltage_base = np.zeros((256,256))
        voltage = np.zeros((256,256))
        cond_sub_base = None
        for i in range(write_times):
            print(f"write_time = {i}")
            tg = start_tg+i*delta_tg
            if read_type == 2:
                if sub_base:
                    voltage_base[need_read] = chip.read_point2(crossbar=need_read, read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)[need_read]
                voltage[need_read] = chip.read_point2(crossbar=need_read, read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)[need_read]
            elif read_type == 3:
                pos = (0,256,0,256)
                if sub_base:
                    voltage_base = chip.read_point3(*pos,read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
                voltage = chip.read_point3(*pos,read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
            if sub_base:
                cond_sub_base = chip.voltage_to_cond(voltage-voltage_base)
            else:
                cond_sub_base = chip.voltage_to_cond(voltage)

            condition_set = (cond_sub_base<threshold)&need_read
            need_read = condition_set
            if plot_cond:
                plot_cond(cond_sub_base,title=f"tg={tg:.2f}-needSet={np.sum(condition_set)}",vmax=1200)

            chip.write_point2(crossbar=condition_set,write_voltage=write_voltage,tg=tg,pulse_width=set_pulse_width,set_device=True)

    def find_good_device(self,row,col,rownum,colnum,cnt=10):
        good_cond = self.good_point
        random.shuffle(row)
        random.shuffle(col)

        select_row,select_col=row[:rownum],col[:colnum]
        rowtmp,coltmp=row[rownum:],col[colnum:]
        
        ansrow=[]
        anscol=[]

        for n in range(cnt):
            flag = False

            
            # 遍历所有选择的行，替换
            for j in select_row:
                k=j
                for i in rowtmp:
                    if np.sum(good_cond[i,select_col])>np.sum(good_cond[k,select_col]):
                        k=i
                if k!=j:
                    rowtmp.remove(k)
                    rowtmp.append(j)
                    flag=True
                ansrow.append(k)
            
            select_row=ansrow
            ansrow=[]

            # 遍历所有选择的列，替换
            for j in select_col:
                k=j
                for i in coltmp:
                    if np.sum(good_cond[select_row,i])>np.sum(good_cond[select_row,k]):
                        k=i
                if k!=j:
                    coltmp.remove(k)
                    coltmp.append(j)
                    flag=True
                anscol.append(k)
            
            select_col=anscol
            anscol=[]

            if not flag:
                break
            # print(n)
        return select_row,select_col
    
    def save_pos(self,row,col,file_path):
        """
            存储找好的点
        """
        np.savez(file_path,row=np.sort(row),col=np.sort(col))