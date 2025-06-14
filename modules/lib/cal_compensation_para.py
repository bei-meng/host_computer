import numpy as np
import random


class COMPENSATION_PARA():
    r_wire = 0.12

    def initop(self,root_path):
        self.root_path = root_path
        # 测处理的行r_out,列r_out
        self.row_r_out = np.load(root_path+"row_r_out.npy")
        self.col_r_out = np.load(root_path+"col_r_out.npy")

        self.col_offset = np.load(root_path+"col_offset.npy")
        self.row_offset = np.load(root_path+"row_offset.npy")

        self.col_value = np.load(root_path+"col_value.npy")
        self.row_value = np.load(root_path+"row_value.npy")

        self.r_wire = 0.12

        self.row_r_out_crossbar = np.repeat(np.array(self.row_r_out), 256).reshape(256, 256)
        self.col_r_out_crossbar = np.repeat(np.array(self.col_r_out), 256).reshape(256, 256).T

        # 每个点对应的线阻，没有考虑row_r_out和col_r_out,这个其实是通过上面的线阻算出来的
        self.r_w_col = np.zeros((256,256))
        self.r_w_row = np.zeros((256,256))
        for row in range(256):
            for col in range(256):
                self.r_w_col[row,col] += (255-row)*self.r_wire if col%2==0 else row*self.r_wire
                self.r_w_row[row,col] += (255-col)*self.r_wire if row%2==1 else col*self.r_wire

    #------------------------------------------------------------------------------------------
    # ******************************** 计算r_out和r_wire(非并行) **********************************
    #------------------------------------------------------------------------------------------   
    def get_A_B_C(self,chip,pos,num,from_row,sub_base=False):
        need_read = np.zeros((256,256),dtype=bool)
        # 计算第一段区间
        weight_pos = np.ix_([i for i in range(pos[0],pos[1])], [num]) if from_row else np.ix_([num],[i for i in range(pos[0],pos[1])])
        need_read[weight_pos] = True
        gain = 1 if (pos[1]-pos[0])<15 else 3
        if sub_base:
            voltage_base = chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
        voltage = chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
        if sub_base:
            voltage -= voltage_base
        a = chip.voltage_to_resistance(voltage = voltage)

        # 计算第二段区间
        need_read[:] = False
        weight_pos = np.ix_([i for i in range(pos[1],pos[2])], [num]) if from_row else np.ix_([num],[i for i in range(pos[1],pos[2])])
        need_read[weight_pos] = True
        gain = 1 if (pos[2]-pos[1])<15 else 3
        if sub_base:
            voltage_base = chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
        voltage = chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
        if sub_base:
            voltage -= voltage_base
        b = chip.voltage_to_resistance(voltage = voltage)

        # 计算第三段区间
        need_read[:] = False
        weight_pos = np.ix_([i for i in range(pos[0],pos[2])], [num]) if from_row else np.ix_([num],[i for i in range(pos[0],pos[2])])
        need_read[weight_pos] = True
        gain = 1 if (pos[2]-pos[0])<15 else 3
        if sub_base:
                voltage_base = chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=from_row,out_type=0)
        voltage = chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=from_row,out_type=0)
        if sub_base:
            voltage -= voltage_base
        c = chip.voltage_to_resistance(voltage = voltage)

        if from_row:
            return a[0,num],b[0,num],c[0,num]
        else:
            return a[num,0],b[num,0],c[num,0]
        
    def get_out(self,chip,pos,row_col_index,from_row,sub_base=False):
        a,b,c = self.get_A_B_C(chip,pos=pos,num=row_col_index,from_row=from_row,sub_base=sub_base)

        base1 = ((c-a)/(c-b))**0.5
        base2 = ((c-b)/(c-a))**0.5
        flag = False
        k=3
        while flag==False and k>0:
            if base1>1:
                R2 = (b-c)*(1+base1)
                R = b-R2
                flag=True
            elif base2>1:
                R1 = (a-c)*(1+base2)
                R = a-R1
                flag=True
            else:
                R = 0
                flag = False
                print("计算错误")
                k-=1
        return R
    
    def calculate_r_out_r_wire(self,chip,calculate_col,index,nums=50,sub_base=False):
        """
            不知道r_out和r_wire的时候用这个函数计算
        """
        if calculate_col:
            R_out_col = np.zeros((256,nums))
            R_wire_col = np.zeros((256,nums))
            for col in index:
                print(f"第{col}列")
                for j in range(nums):
                    if col%2==0:
                        R_out_col[col,j] = self.get_out(chip,(200,250,256),col,from_row=True,sub_base=sub_base)
                        R_wire_col[col,j] = self.get_out(chip,(0,50,56),col,from_row=True,sub_base=sub_base)
                    else:
                        R_out_col[col,j] = self.get_out(chip,(0,6,56),col,from_row=True,sub_base=sub_base)
                        R_wire_col[col,j] = self.get_out(chip,(200,206,256),col,from_row=True,sub_base=sub_base)

            R_out_mean = np.mean(R_out_col,axis=1)*1000
            R_wire_mean = (np.mean(R_wire_col,axis=1)*1000-R_out_mean)/200
            return R_out_mean,R_wire_mean
        else:
            R_out_row = np.zeros((256,nums))
            R_wire_row = np.zeros((256,nums))
            for row in index:
                print(f"第{col}行")
                for j in range(nums):
                    if row%2==0:
                        R_out_row[row,j] = self.get_out(chip,(0,6,56),row,from_row=False,sub_base=sub_base)
                        R_wire_row[row,j] = self.get_out(chip,(200,206,256),row,from_row=False,sub_base=sub_base)
                    else:
                        R_out_row[row,j] = self.get_out(chip,(200,250,256),row,from_row=False,sub_base=sub_base)
                        R_wire_row[row,j] = self.get_out(chip,(0,50,56),row,from_row=False,sub_base=sub_base)


            R_out_mean = np.mean(R_out_row,axis=1)*1000
            R_wire_mean = (np.mean(R_wire_row,axis=1)*1000-R_out_mean)/200
            return R_out_mean,R_wire_mean
        

    def calculate_r_out_from_r_wire(self,chip,num,from_row=True):
        """
            知道单位线阻的时候可以用这个函数计算r_out
        """
        point_read = np.zeros((256,256))
        sum_read = np.zeros((256))
        num = 40
        for i in range(num):
            crossbar = np.ones((256,256))
            voltage,cond,resistence = chip.read4(crossbar=crossbar,row_index=None,col_index=None,read_voltage=0.1,tg=5,gain=1,sub_base=True,from_row=from_row,split_type=0,row_type=0,col_type=0)
            print(np.max(voltage))

            point_read+=resistence

            point_read+=resistence

            row_index = [i for i in range(256)]
            col_index = [i for i in range(256)]
            v,c,resistence = chip.read4(crossbar=None,row_index=row_index,col_index=col_index,read_voltage=0.1,tg=5,gain=3,sub_base=True,from_row=from_row,split_type=3,row_type=0,col_type=0)
            print(np.max(v))

            sum_read+=resistence

        point_read=point_read/num
        sum_read=sum_read/num
        return point_read,sum_read
    
    def get_r_out(self,point_read,sum_read,filename,from_row=True):
        """
            配合上面的函数一起的
        """
        point_read2=point_read*1000
        sum_read2=sum_read*1000

        r_out = np.zeros((256))
        if from_row:
            for row in range(256):
                for col in range(256):
                    point_read2[row,col] -= (255-row)*0.12 if col%2==0 else row*0.12

            for col in range(256):
                left = 10
                right = 30
                mid = 0
                while right-left>0.01:
                    mid = (left+right)/2
                    tmp = point_read2[0,col]-mid
                    
                    for row in range(1,256):
                        tmp = (tmp+0.12)*(point_read2[row,col]-mid)/(tmp+0.12+point_read2[row,col]-mid)
                    if tmp>sum_read2[col]-mid:
                        right=mid
                    else:
                        left=mid
                r_out[col]=mid
        else:
            for row in range(256):
                for col in range(256):
                    point_read2[row,col] -= (255-col)*0.12 if row%2==1 else col*0.12

            for row in range(256):
                left = 10
                right = 30
                mid = 0
                while right-left>0.01:
                    mid = (left+right)/2
                    tmp = point_read2[row,0]-mid
                    
                    for col in range(1,256):
                        tmp = (tmp+0.12)*(point_read2[row,col]-mid)/(tmp+0.12+point_read2[row,col]-mid)
                    if tmp>sum_read2[row]-mid:
                        right=mid
                    else:
                        left=mid
                r_out[row]=mid
        np.save(filename,r_out)
        return r_out
    

    def get_compare(self,chip,col,value=0.875,oddoffset=0,evenoffset=2):
        ans = np.zeros((5,256))
        # ---------------------------------------------------------------逐点读，并去除线组和R_out的影响
        need_read = np.zeros((256,256),dtype=bool)
        need_read[:,col]=True
        voltage_base = chip.read_point2(crossbar=need_read,read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
        voltage = chip.read_point2(crossbar=need_read,read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
        resistence = chip.voltage_to_resistance(voltage=voltage-voltage_base)
        point_read_r = chip.compensation.compensation_point(resistence=resistence,from_row=True,return_type=2)[:,col]
        point_read_c = 1/point_read_r*1e6

        ans[0,0]=point_read_c[0]
        for i in range(1,256):
            ans[0,i]=point_read_c[i]+ans[0,i-1]

        # ---------------------------------------------------------------多行累积输出结果
        for i in range(256):
            need_read[:] = False
            need_read[:i+1,col]=True
            gain = 1 if i < 20 else 3
            voltage_base=chip.compute(crossbar=need_read,read_voltage=0,tg=5,gain=gain,from_row=True,out_type=0)
            voltage=chip.compute(crossbar=need_read,read_voltage=0.1,tg=5,gain=gain,from_row=True,out_type=0)
            if np.max(voltage)>1.1:
                print(np.max(voltage))
            ans[1,i] = chip.voltage_to_cond(voltage = voltage-voltage_base)[0,col]

        # ---------------------------------------------------------------重构实际输出值
        r_wire = 0.12
        r_out = chip.compensation.col_r_out[col]

        ans[2,0] = point_read_r[0]
        for i in range(1,256):
            ans[2,i] = (ans[2,i-1]+r_wire)*point_read_r[i]/(ans[2,i-1]+r_wire+point_read_r[i])

        for i in range(256):
            rw_sum = (255-i)*r_wire if col%2==0 else 0
            ans[2,i] += rw_sum + r_out

        ans[2,:] = 1/ans[2,:]*1e6

        # ---------------------------------------------------------------实际输出值减去r_out
        ans[3,:] = 1/ans[1,:]*1e6
        for i in range(256):
            rw_sum = (255-i)*r_wire if col%2==0 else 0
            ans[3,i] -= rw_sum + r_out
        ans[3,:] = 1/ans[3,:]*1e6

        # ---------------------------------------------------------------实际输出值减去减去value
        ans[4,:] = 1/ans[1,:]*1e6
        for i in range(256):
            max_index,min_index = i,0
            rw_sum = (255-i)*r_wire+evenoffset if col%2==0 else 0+oddoffset
            ans[4,i] -= rw_sum + r_out + self.r_wire*(max_index**value)
        ans[4,:] = 1/ans[4,:]*1e6
        return ans