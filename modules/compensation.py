from command import CMD,CmdData,Packet
from command.singleCmdInfo import *
from pc import PS
import numpy as np

latchsize=256

root_path = "../modules/data/"
# 测处理的行r_out,列r_out
row_r_out = np.load(root_path+"chip_1_4_row_r_out_0_50_56.npy")
col_r_out = np.load(root_path+"chip_1_4_col_r_out_0_50_56.npy")


row_r_out_crossbar = np.repeat(np.array(row_r_out), 256).reshape(256, 256)
col_r_out_crossbar = np.repeat(np.array(col_r_out), 256).reshape(256, 256).T


# 测出来的行单位线阻，列单位线阻
r_w_row = np.load(root_path+"chip_1_4_row_r_wire_0_50_56.npy")
r_w_col = np.load(root_path+"chip_1_4_col_r_wire_0_50_56.npy")

# 每个点对应的线阻，没有考虑row_r_out和col_r_out,这个其实是通过上面的线阻算出来的
# r_w_crossbar = np.zeros((256,256))
# for row in range(256):
#     for col in range(256):
#         r_w_crossbar[row,col] = (255-row)*r_w_col[col] if col%2==0 else row*r_w_col[col]
#         r_w_crossbar[row,col] += (255-col)*r_w_row[row] if row%2==1 else col*r_w_row[row]
r_w_crossbar = np.load(root_path+"chip_1_4_r_w_crossbar_0_50_56.npy")

class COMPENSATION():
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
            resistence = resistence*1e3 - r_w_crossbar - col_r_out_crossbar
        else:
            resistence = resistence*1e3 - r_w_crossbar - row_r_out_crossbar
        if return_type==0:
            return 1/resistence*1e6
        elif return_type==1:
            return resistence*1e-3
        else:
            return resistence
        

    def compensation_forward(self,index,resistence,from_row=True,value=0.875,return_type = 0):
        """
            index表示输入的行号,或者列号
            resistence为输出的电阻结果
            return_type:
                =0,返回电导,uS
                =1,返回电阻,kΩ
                =2,返回电阻,Ω
        """
        min_index,max_index = np.min(index),np.max(index)
        nums= len(index)
        if from_row:
            col_rw = np.array([(256-max_index)*r_w_col[i] if i%2==0 else (min_index)*r_w_col[i] for i in range(latchsize)])
            resistence = resistence*1e3 - col_r_out - col_rw - r_w_col*(nums**value)
        else:
            row_rw = np.array([(256-max_index)*r_w_row[i] if i%2==1 else (min_index)*r_w_row[i] for i in range(latchsize)])
            resistence = resistence*1e3 - row_r_out - row_rw - r_w_row*(nums**value)

        if return_type==0:
            return 1/resistence*1e6
        elif return_type==1:
            return resistence*1e-3
        else:
            return resistence