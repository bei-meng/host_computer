import numpy as np


latchsize=256



class COMPENSATION():
    def initop(self,root_path):
        self.root_path = root_path
        # 测处理的行r_out,列r_out
        self.row_r_out = np.load(root_path+"row_r_out.npy")
        self.col_r_out = np.load(root_path+"col_r_out.npy")

        self.col_offset = np.load(root_path+"col_offset.npy")
        self.row_offset = np.load(root_path+"row_offset.npy")

        self.col_value = np.load(root_path+"col_value.npy")
        self.row_value = np.load(root_path+"row_value.npy")

        self.col_gain_r_mult = 1/np.load(root_path + "row_gain_r_mult.npy")
        self.row_gain_r_mult = 1/np.load(root_path + "row_gain_r_mult.npy")

        # 这个因子是给电导的
        self.col_ans_mult1 = 1/np.load(root_path + "row_mult1.npy")
        self.row_ans_mult1 = 1/np.load(root_path + "row_mult1.npy")

        # self.row_offset_parallel_16 = np.load(root_path+"row_offset_parallel_16.npy")
        # self.col_offset_parallel_16 = np.load(root_path+"col_offset_parallel_16.npy")

        # self.row_value_parallel_16 = np.load(root_path+"row_value_parallel_16.npy")
        # self.col_value_parallel_16 = np.load(root_path+"col_value_parallel_16.npy")


        # self.row_offset_parallel_8 = np.load(root_path+"row_offset_parallel_8.npy")
        # self.col_offset_parallel_8 = np.load(root_path+"col_offset_parallel_8.npy")

        # self.row_value_parallel_8 = np.load(root_path+"row_value_parallel_8.npy")
        # self.col_value_parallel_8 = np.load(root_path+"col_value_parallel_8.npy")

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
        

    def compensation_forward(self,index,resistence,r_out = None,gain_r_mult = None,offset = None,value = None,mult = None,from_row=True,return_type = 0):
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
        # 线阻的影响
        rw = np.array([(255-max_index)*self.r_wire if (from_row and i%2==0) or (not from_row and i%2==1) else (min_index)*self.r_wire for i in range(latchsize)])
        # r_out的影响
        if r_out is None:
            r_out = self.col_r_out if from_row else self.row_r_out
        # 因为读误差，计算误差r_out不准,拟合后得到对应的offset
        if offset is None:
            offset = self.col_offset if from_row else self.row_offset
        if value is None:
            value = self.col_value if from_row else self.row_value
        if gain_r_mult is None:
            gain_r_mult = self.col_gain_r_mult if from_row else self.row_gain_r_mult
        if mult is None:
            mult = self.col_ans_mult1 if from_row else self.row_ans_mult1

        if gain_r_mult is not None:
            resistence = resistence * gain_r_mult
        # 得到实际阻值
        resistence = resistence*1e3 - r_out - rw + offset
        if value is not None:
            resistence -= self.r_wire*((max_index-min_index+1)/nums)*(nums**value)
        if mult is not None:
            resistence *= mult
        resistence[resistence<1]=1
        if return_type==0:
            return 1/resistence*1e6
        elif return_type==1:
            return resistence*1e-3
        elif return_type==2:
            return resistence


