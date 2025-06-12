from typing import List, Union
import numpy as np
class CHIPSETTING:
    # 芯片配置
    deviceType = 0                                              # 0为ReRAM,1为ECRAM
    IsRERAM512 = False                                          # 是否是reream512
    IsNew32 = False                                             # 是否是新的32路tia的板子

    chip_bank_num = 8                                           # 8个bank
    chip_tia_num = 16                                           # 16个tia
    chip_latch_num = 256                                        # 256个latch

    # FPGA配置
    REG_NUM = 32                                                # 可用32个通用寄存器    

    INS_RAM_ADDR_LENGTH = 10                                    # 指令RAM的地址长度 2^10=1024
    BGE_INS_ADDR_START_POS = 14                                 # bge中指令地址bit位置的起始位置

    din_ram_length = 256                                        # din_ram可以存256个数据
    din_ram_size = 32                                           # 每个数据长32bit

    dout_ram_length = 128                                       # dout_ram可以存128个数据,本来是256,但是现在128以后的不知道为什么不能用
    dout_ram_size = 256                                         # 每个数据长256bit
    dout_ram_size_B = 32                                        # 数据长32B

    ins_ram_length = 280                                        # ins_ram可以存1024个数据,但是由于下面TCP的限制导致每次只能发256条指令
    ins_ram_size = 32                                           # 每个数据长32bit


    # 空间换时间
    num_to_bank_index = None
    num_to_tia_row = None
    num_to_tia_col = None
    num_to_bank_index_tia_row = None


    tia_map = None                                              # 几路TIA并行

    def __init__(self,deviceType:int,IsNew32:bool=False,IsRERAM512:bool=False):
        self.set_device(deviceType,IsNew32,IsRERAM512)

    #------------------------------------------------------------------------------------------
    # ************************************** 各种索引映射 **************************************
    #------------------------------------------------------------------------------------------
    def set_device(self,deviceType:int,IsNew32:bool=False,IsRERAM512:bool=False):
        self.deviceType = deviceType
        self.IsRERAM512 = IsRERAM512
        self.set_new32(IsNew32)
        # 空间换时间
        self.num_to_bank_index = [self._numToBank_Index(i) for i in range(self.chip_latch_num)]
        self.num_to_tia_row = [self._TIA_index_map(i,col=False) for i in range(self.chip_latch_num)]
        self.num_to_tia_col = [self._TIA_index_map(i,col=True) for i in range(self.chip_latch_num)]
        self.num_to_bank_index_tia_row = [(bank,index,tia) for (bank,index),tia in zip(self.num_to_bank_index,self.num_to_tia_row)]
        self.num_to_bank_index_tia_col = [(bank,index,tia) for (bank,index),tia in zip(self.num_to_bank_index,self.num_to_tia_col)]

    def set_new32(self,IsNew32:bool):
        self.IsNew32 = IsNew32
        if self.IsNew32:
            self.dout_ram_length = 256
            self.ins_ram_length = 280
            self.chip_tia_num = 32
            self.dout_ram_size = 512
            self.dout_ram_size_B = 64
        else:
            self.chip_tia_num = 16
            self.dout_ram_size = 256
            self.dout_ram_size_B = 32

    
    def _numToBank_Index(self,num:int) -> tuple[int,int]:
        """
            Args:
                num: 行/列号, 从0开始

            Returns:
                tuple: (bank, index) 其中 bank[0:8] 和 index[0:31] 坐标从0开始
        """
        num += 1
        assert num >=0 and num <= self.chip_latch_num,"numToBank_Index: num超过范围!"
        # 先判断奇数偶数
        if num&1:
            index_base,index_offset = 64,1
            bank_base = 0
        else:
            index_base,index_offset = 64,2
            bank_base = 4

        bank_offset = int((num-index_offset)/index_base)
        bank = bank_base + bank_offset
        index = int((num - index_offset - bank_offset * index_base) / 2)

        return bank, index

    def bank_to_num(self,bank_data:list) -> list[int]:
        """
            Args:
                bank_data: 包含需要映射的bank坐标的列表, 例: [0, 1]

            Returns:
                list: [ row_num/col_num ], 返回对应bank包含的所有的行/列号, 因为行/列号与bank的对应关系相同
        """
        bank_list = [[] for i in range(self.chip_bank_num)]
        for i in range(self.chip_latch_num):
            bank,_ = self.self.num_to_bank_index[i]
            bank_list[bank].append(i)
        res = []
        for i in bank_data:
            res = res + bank_list[i]
        return res
    
    def bank_split_from_index(self,index:list[int]):
        """
            Args:
                index: 行/列索引

            Returns:
                [[int,int,...],[int,int,...],...]
                返回的每个bank中的列表都是行列的index32位数据
        """
        if len(index)==1:
            return [index]
        bank_data = [[] for _ in range(self.chip_bank_num)]
        for num in index:
            bank, _ = self.num_to_bank_index[num]
            bank_data[bank].append(num)
        return [bank for bank in bank_data if bank]
    
    def bank_split(self,data:list[tuple[int,int,int,int,int]],
                   all_data:bool = False) -> Union[list[list[int]],list[list[tuple[int,int,int,int,int]]]]:
        """
            Args:
                data: 数据为(pos, row_num/col_num, bank, index, tia_num)的列表
                all_data: 是否返回完整格式的数据(pos, row_num/col_num, bank, index, tia_num)

            Returns:
                list0 [ list1 [int] ], 将数据切分到对应的bank中, list1表示在一个bank中的行/列号
                每个list1都不为空
        """
        bank_data = [[] for _ in range(self.chip_bank_num)]
        for j in data:
            bank_data[j[2]].append(j if all_data else j[1])
        return [bank for bank in bank_data if bank]
    
    def tia_to_num(self,tia_data:list,row=None):
        """
            Args:
                tia_data: 包含需要映射的tia坐标的列表, 例: [0, 1]
                row: 因为不同device的 行/列tia映射不一样

            Returns:
                list: [ row_num/col_num ], 返回对应tia包含的所有的行/列号, 因为行/列号与tia的对应关系不相同
        """
        tia_list = [[] for i in range(self.chip_tia_num)]
        for i in range(self.chip_latch_num):
            num = self.TIA_index_map(i,col= not row)
            tia_list[num].append(i)
        res = []
        for i in tia_data:
            res = res + tia_list[i]
        return res
    
    def tia_split_from_index(self,index:list[int],col:bool=True) -> list[list[tuple[int,int,int,int,int]]]:
        """
            Args:
                index: 行/列索引

            Returns:
                [[int,int,...],[int,int,...],...]
        """
        if len(index)==1:
            return [index]
        batch = []
        tia = [[] for _ in range(self.chip_tia_num)]
        # ----------------------------------------------分成几路TIA
        if self.tia_map:
            tia_map = [self.tia_map[i] for i in self.num_to_tia_col] if col else [self.tia_map[i] for i in self.num_to_tia_row]
        else:
            tia_map = self.num_to_tia_col if col else self.num_to_tia_row
        # ----------------------------------------------行/列号映射为TIA
        for num in index:
            tia[tia_map[num]].append(num)
        
        tia = [sublist for sublist in tia if sublist]
        maxNum = 0
        for sublist in tia:
            maxNum = max(maxNum,len(sublist))
        # ----------------------------------------------每路TIA选一路
        while maxNum:
            batch.append([sublist.pop() for sublist in tia if sublist])
            maxNum -=1

        return batch

    
    def tia_split(self,data:list[tuple[int,int,int,int,int]],tia_split:Union[list[int]|None]=None,
                  check_tia = True) -> list[list[tuple[int,int,int,int,int]]]:
        """
            Args:
                data: 数据为(pos, row_num/col_num, bank, index, tia_num)的列表
                check_tia: 表示是否需要处理一路TIA只能映射一列的问题

            Returns:
                list0 [ list1 [tuple] ], 数据根据TIA数量, 切分到对应的处理批次中\n
                每次读操作处理list1里面的数据,
                每个list1都不为空
        """
        read_batch = []
        if check_tia:
            tia16 = [[] for _ in range(self.chip_tia_num)]
            for i in data:
                tia16[tia_split[i[4]] if tia_split else i[4]].append(i)
            tia16 = [sublist for sublist in tia16 if sublist]
            maxNum = 0
            for sublist in tia16:
                maxNum = max(maxNum,len(sublist))
            # ----------------------------------------------每路TIA选一路
            while maxNum:
                read_batch.append([sublist.pop() for sublist in tia16 if sublist])
                maxNum -=1
                # tia16 = [sublist for sublist in tia16 if sublist]
        else:
            read_batch.append(data)

        return read_batch
    
    def get_bank_index32(self,num:list) -> tuple[int,int]:
        """
            Args:
                num: 行/列号的列表, 必须都在同一个bank里面!

            Returns:
                tuple[int,int]: 经过处理过的bank,index的值,可以直接作为指令数据下发
        """
        bank,index = 0,0
        for i in num:
            bank_tmp,index_tmp = self.num_to_bank_index[i]
            bank = bank | (1<<bank_tmp)
            index = index | (1<<index_tmp)
        return bank,index

    def get_bank_index_tia(self,num:list,col:bool) -> list[tuple[int,int,int,int,int]]:
        if col:
            return [(i,v)+self.num_to_bank_index_tia_col[v] for i,v in enumerate(num)]
        else:
            return [(i,v)+self.num_to_bank_index_tia_row[v] for i,v in enumerate(num)]
    
    def _get_bank_index_tia(self,num:list,col:bool) -> list[tuple[int,int,int,int,int]]:
        """
            Args:
                num: 任意行/列号的列表
                col: 是否是列

            Returns:
                list[tuple[int,int,int,int,int]]: 列表里面的每个数据都是对应行列号的映射结果
                为元组(pos, row_num/col_num, bank, index, tia_num)的列表
        """
        res = []
        for pos,v in enumerate(num):
            bank,index = self.num_to_bank_index[v]
            tia = self.TIA_index_map(v,col=col)
            res.append((pos,v,bank,index,tia))
        return res
    
    def TIA_index_map(self,num,col=True):
        return self.num_to_tia_col[num] if col else self.num_to_tia_row[num]
    
    def TIA_index_map_512k(self,num):
        return self._TIA_index_map(num,col=False)

    def _TIA_index_map(self,num,col=True):
        """
            注意: num从0索引开始
            将对应的行或列索引映射为对应的TIA偏移
        """
        if self.IsNew32:
            return self._TIA_index_map_new32(num,col)
        num += 1
        assert num > 0 and num < 257,"numToBank_Index: num超过范围!"
        if self.deviceType==0 and col:
            if (self.IsRERAM512):   # 512k阵列的映射不同
                # 先判断奇数偶数
                if num&1:
                    index_base,index_offset = 32,1
                    TIA_base = 0
                else:
                    index_base,index_offset = 32,2
                    TIA_base = 8
            else:
                # 先判断奇数偶数
                if num&1:
                    index_base,index_offset = 32,1
                    TIA_base = 8
                else:
                    index_base,index_offset = 32,2
                    TIA_base = 0
        else:
            # 先判断奇数偶数
            if num&1:
                index_base,index_offset = 32,1
                TIA_base = 0
            else:
                index_base,index_offset = 32,2
                TIA_base = 8
                
        TIA_offset = int((num-index_offset)/index_base)

        return TIA_base+TIA_offset
    
    def _TIA_index_map_new32(self,num,col):
        """
            注意: num从0索引开始
            将对应的行或列索引映射为对应的TIA偏移
        """
        num += 1
        assert num > 0 and num < 257,"numToBank_Index: num超过范围!"

        if self.deviceType==0:
            if col:
                if (self.IsRERAM512):   # 512k阵列的映射不同
                    # 先判断奇数偶数
                    if num&1:
                        index_base,index_offset = 16,1
                        TIA_base = 0
                    else:
                        index_base,index_offset = 16,2
                        TIA_base = 16
                else:
                    # 奇数列，TIA从16开始
                    # 先判断奇数偶数
                    if num&1:
                        index_base,index_offset = 16,1
                        TIA_base = 16
                    else:
                        index_base,index_offset = 16,2
                        TIA_base = 0
            else:
                # 奇数行，TIA从0开始
                # 先判断奇数偶数
                if num&1:
                    index_base,index_offset = 16,1
                    TIA_base = 0
                else:
                    index_base,index_offset = 16,2
                    TIA_base = 16

            TIA_offset = int((num-index_offset)/index_base)
            return TIA_base+TIA_offset
        else:
            if col:
                # 奇数列0-14
                if num&1:
                    index_base,index_offset = 32,1
                    TIA_base = 0
                # 偶数行17-31
                else:
                    index_base,index_offset = 32,2
                    TIA_base = 17
            else:
                # 先判断奇数偶数
                if num&1:
                    index_base,index_offset = 32,1
                    TIA_base = 1
                else:
                    index_base,index_offset = 32,2
                    TIA_base = 17
                
            TIA_offset = int((num-index_offset)/index_base)
            return TIA_base+TIA_offset*2
        

    def check_din_ram(self,din_ram_data,din_ram_start):
        num = len(din_ram_data)
        assert num+din_ram_start <= self.din_ram_length,f"check_din_ram: din_ram:{num+din_ram_start}超过界限。"
        return num