import numpy as np


latchsize=256



class COMPENSATION():
    def initop(self,root_path):
        self.root_path = root_path
        # 测处理的行r_out,列r_out
        self.row_r_out = np.load(root_path+"row_r_out.npy")
        self.col_r_out = np.load(root_path+"col_r_out.npy")

        self.r_wire = 0.12

        self.row_r_out_crossbar = np.repeat(np.array(self.row_r_out), 256).reshape(256, 256)
        self.col_r_out_crossbar = np.repeat(np.array(self.col_r_out), 256).reshape(256, 256).T

        # 每个点对应的线阻，没有考虑row_r_out和col_r_out,这个其实是通过上面的线阻算出来的
        self.r_w_col = np.zeros((256,256))
        self.r_w_row = np.zeros((256,256))
        for row in range(256):
            for col in range(256):
                self.r_w_col[row,col] = (255-row)*self.r_wire if col%2==0 else row*self.r_wire
                self.r_w_row[row,col] += (255-col)*self.r_wire if row%2==1 else col*self.r_wire

    def compensation_point(self,resistence,from_row=True,return_type = 0):
        """
            resistence为一个256*256的np数组
            电阻单位为kΩ
            return_type:
                =0,返回电导,uS
                =1,返回电阻,kΩ
                =2,返回电阻,Ω

            读的点实际值电阻值需要减去,线阻,行输入的r_out,列的r_out
        """
        if from_row:
            resistence = resistence*1e3 - self.r_w_col - self.col_r_out_crossbar
        else:
            resistence = resistence*1e3 - self.r_w_row - self.row_r_out_crossbar
        if return_type==0:
            return 1/resistence*1e6
        elif return_type==1:
            return resistence*1e-3
        elif return_type==2:
            return resistence
        

    def compensation_forward(self,index,resistence,from_row=True,return_type = 0,
                             compensation_para:dict={
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
            index表示输入的行号,或者列号
            resistence为输出的电阻结果kΩ
            return_type:
                =0,返回电导,uS
                =1,返回电阻,kΩ
                =2,返回电阻,Ω
        """
        min_index,max_index = np.min(index),np.max(index)
        nums= len(index)
        # 奇数列，偶数列的偏移
        offset = np.array([compensation_para["even_offset"] if i%2 == 0 else compensation_para["odd_offset"] for i in range(latchsize)])
        # 奇数列，偶数列的mult
        mult = np.array([compensation_para["even_mult"] if i%2 == 0 else compensation_para["odd_mult"] for i in range(latchsize)])
        mult = mult*compensation_para["all_mult"]
        # 线阻的影响
        rw = np.array([(255-max_index)*self.r_wire if (from_row and i%2==0) or (not from_row and i%2==1) else (min_index)*self.r_wire for i in range(latchsize)])

        resistence = resistence*1e3 - self.row_r_out - rw - offset
        if compensation_para["add_wire"]:
            resistence -= self.r_wire*((max_index-min_index+1)/nums)*(nums**compensation_para["value"])

        resistence *= mult
        if return_type==0:
            return 1/resistence*1e6
        elif return_type==1:
            return resistence*1e-3
        elif return_type==2:
            return resistence
    

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
        

    def calculate_r_out_from_r_wire(self,chip,num):
        """
            知道单位线阻的时候可以用这个函数计算r_out
        """
        point_read = np.zeros((256,256))
        sum_read = np.zeros((1,256))
        num = 40
        for i in range(num):
            voltage_base = chip.read_point3(0,256,0,256,read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
            voltage = chip.read_point3(0,256,0,256,read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
            print(np.max(voltage))
            resistence = chip.voltage_to_resistance(voltage=voltage-voltage_base)

            point_read+=resistence

            voltage_base=chip.compute(crossbar=np.ones((256,256)),read_voltage=0,tg=5,gain=3,from_row=True,out_type=0)
            voltage=chip.compute(crossbar=np.ones((256,256)),read_voltage=0.1,tg=5,gain=3,from_row=True,out_type=0)
            # print(voltage.shape)
            print(np.max(voltage))
            resistence = chip.voltage_to_resistance(voltage = voltage-voltage_base)

            sum_read+=resistence

        point_read=point_read/num
        sum_read=sum_read/num
        return point_read,sum_read
    
    def get_r_out(self,point_read,sum_read,filename):
        """
            配合上面的函数一起的
        """
        point_read2=point_read*1000
        sum_read2=sum_read*1000

        for row in range(256):
            for col in range(256):
                point_read2[row,col] -= (255-row)*0.12 if col%2==0 else row*0.12

        r_out = np.zeros((256))
        for col in range(256):
            left = 10
            right = 30
            mid = 0
            while right-left>0.01:
                mid = (left+right)/2
                tmp = point_read2[0,col]-mid
                
                for row in range(1,256):
                    tmp = (tmp+0.12)*(point_read2[row,col]-mid)/(tmp+0.12+point_read2[row,col]-mid)
                if tmp>sum_read2[0,col]-mid:
                    right=mid
                else:
                    left=mid
            r_out[col]=mid
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


