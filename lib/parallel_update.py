# :param num:0-1之间的随机数
# :param dimension: 序列是第几维度，乘法只需要2维度，即0或者1

# :return res: 二进制序列

import random
import numpy as np
from scipy.stats import qmc

class Sampler:
    def __init__(self,sampler_type:str = "halton",max_length:int=2**16):
        """
        :param sampler_type: 设置低差异性序列的采样类型
        :param max_length: 使用的最大长度
        """
        self.sampler_type=sampler_type
        self.sampler = qmc.Halton(d=2, scramble=False) if sampler_type == "halton" else qmc.Sobol(d=2, scramble=False)
        
        self.current_length=0
        self.max_length=max_length

        self.reset()

    def random(self,n=1):
        res = []
        while n>0:
            n = n-1
            tmp = self.sampler.random(1)
            res.append((tmp[0,0],tmp[0,1]))
            self.current_length+=1
            if self.current_length>=self.max_length:
                self.reset()
        return res

    def reset(self):
        self.sampler.reset()
        self.sampler.random(n=1)
        self.current_length=0


    def get_random_sequence(self,x:np.ndarray,delta:np.ndarray,bit_length:int = 10):
        """
        :param x: 输入,n*1的np矩阵
        :param delta: 反向传回的误差,1*m的np矩阵
        :param bit_length: 使用的序列长度

        :return result对应的01脉冲序列,以及对应的脉冲需要的缩放倍数
        """
        x_max = np.max(abs(x))
        delta_max = np.max(abs(delta))

        result = []
        sequence_random = self.random(bit_length)
        for x_random,delta_random in sequence_random:
            x_random *= x_max
            delta_random *= delta_max
            result.append((x_random<x,delta_random<delta))
        return result,x_max*delta_max
        
    def get_random_sequence(self,x:np.ndarray,delta:np.ndarray,bit_length:int = 10):
        """
        :param x: 输入,n*1的np矩阵
        :param delta: 反向传回的误差,1*m的np矩阵
        :param bit_length: 使用的序列长度

        :return result对应的01脉冲序列,以及对应的脉冲需要的缩放倍数
        """
        x_max = np.max(abs(x))
        delta_max = np.max(abs(delta))

        result = []
        sequence_random = self.random(bit_length)
        for x_random,delta_random in sequence_random:
            x_random *= x_max
            delta_random *= delta_max
            result.append((x_random<x,delta_random<delta))
        return result,x_max*delta_max

    def get_random_compute_res(self,x:np.ndarray,delta:np.ndarray,bit_length:int = 10):
        """
        :param x: 输入
        :param delta: 反向传回的误差
        :param bit_length: 使用的序列长度

        :return 随机计算乘法的结果,以及software计算的结果
        """
        result,scale = self.get_random_sequence(x = x,delta = delta,bit_length = bit_length)
        row,col = result[0][0].shape[0],result[0][1].shape[1]
        res_random = np.zeros((row,col))
        res = np.dot(x,delta)

        for i in range(bit_length):
            res_random += np.dot(result[i][0],result[i][1])

        return res_random/bit_length*scale,res