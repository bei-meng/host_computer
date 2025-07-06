import numpy as np
import random


class WIRE_RESISTANCE():
    # r_wire = 0.12               # 线阻0.12Ω
    # r_device = 2e3              # 2kΩ对应500uS
    # row_num = 256               # 有多少行
    # r_out = 18                  # 外部线阻18欧姆

    # def __init__(self,r_device=2e3,r_wire=0.12,r_out=18,row_num=256):
    #     """
    #         初始化线阻模型参数
    #     """
    #     self.r_device = r_device
    #     self.r_wire = 0.12
    #     self.r_out = r_out
    #     self.row_num = row_num


    def get_result(self,r_device=2e3,r_wire=0.12,r_out=18,row_num=256):
        expected = np.zeros(row_num)
        expected_with_r_out = np.zeros(row_num)
        actual = np.zeros(row_num)
        actual_with_r_out = np.zeros(row_num)


        c_device = 1/r_device
        c_device_with_r_out = 1/(r_device + r_out)
        # 计算期望输出值，有没有r_out
        expected[0] = c_device
        expected_with_r_out[0] = c_device_with_r_out
        for i in range(1,row_num):
            expected[i] += expected[i-1]+c_device
            expected_with_r_out[i] = expected_with_r_out[i-1]+c_device_with_r_out
        
        # 计算实际输出值
        actual[0] = c_device
        actual_with_r_out[0] = c_device

        for i in range(1,row_num):
            actual[i] = (1/actual[i-1]+r_wire+r_device)/((1/actual[i-1]+r_wire)*r_device)

        for i in range(0,row_num):
            actual_with_r_out[i] = 1/(1/actual[i] + r_out)

        return expected,expected_with_r_out,actual,actual_with_r_out
    
    def get_result2(self,r_device,r_wire=0.12,r_out=18,row_num=256):
        """
            需要给出device数组
        """
        assert type(r_device)==np.ndarray and len(r_device)==256,f"r_device必须为含有{row_num}个元素的np数组"
        expected = np.zeros(row_num)
        expected_with_r_out = np.zeros(row_num)
        actual = np.zeros(row_num)
        actual_with_r_out = np.zeros(row_num)


        # 计算期望输出值，有没有r_out
        expected[0] = 1/r_device[0]
        expected_with_r_out[0] = 1/(r_device[0] + r_out)
        for i in range(1,row_num):
            expected[i] += expected[i-1]+1/r_device[i]
            # + r_wire*(255-i)
            expected_with_r_out[i] = expected_with_r_out[i-1]+1/(r_device[i] + r_out )
        
        # 计算实际输出值
        actual[0] = 1/r_device[0]
        actual_with_r_out[0] = 1/r_device[0]
        for i in range(1,row_num):
            actual[i] = 1/(1/actual[i-1] + r_wire) + 1/r_device[i]
            
            # (1/actual[i-1] + r_wire + r_device[i])/((1/actual[i-1] + r_wire) * r_device[i])
            # if actual[i]<actual[i-1]:
            #     print("不太对劲",1/actual[i-1],1/actual[i],r_wire)

        for i in range(0,row_num):
            actual_with_r_out[i] = 1/(1/actual[i] + r_out)

        return expected,expected_with_r_out,actual,actual_with_r_out

