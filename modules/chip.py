from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS
from modules.adc import ADC
from modules.dac import DAC
from modules.clk_manager import CLK_MANAGER
import numpy as np
import time

from typing import List, Union

class CHIP():
    """
        对chip进行的操作
    """
    deviceType = 0                  # 器件类型0: RERAM,1: ECRAM

    op_mode = None                  # 当前所处模式
    from_row = True                 # 从行/列读写
    read_voltage = None             # 读写电压
    write_voltage = None            # 写电压

    chip_bank_num = 8
    chip_tia_num = 16
    chip_latch_num = 256

    din_ram_threshold = 256
    dout_ram_threshold = 128
    ins_ram_threshold = 280#1024

    ps = None
    adc = None
    dac = None
    clk_manager = None

    init = True

    def __init__(self, ps:PS,init = True):
        self.ps = ps
        self.init = init
        self.initOp()
        self.adc = ADC(ps,init)
        self.dac = DAC(ps,init)
        self.clk_manager = CLK_MANAGER(ps,init)

    def get_setting_info(self):
        """
            输出相关信息
        """
        device = "ECRAM" if self.deviceType else "ReRAM"
        row_col = "行" if self.from_row else "列"
        if self.op_mode == "read":
            res = f"操作模式: {self.op_mode}\t器件: {device}\t读电压: {self.read_voltage}v\t从行\列给电压: {row_col}\tTIA增益: {self.adc.gain}"
        elif self.op_mode == "write":
            res = f"操作模式: {self.op_mode}\t器件: {device}\t写电压: {self.write_voltage}v\t从行\列给电压: {row_col}\t脉宽: {self.clk_manager.pulse_cyc}"
        else:
            res = f"未配置操作模式。"
        return res

    #------------------------------------------------------------------------------------------
    # ********************************** 器件初始化及其他操作 ***********************************
    #------------------------------------------------------------------------------------------
    def initOp(self):
        """
            chip的初始化操作
        """
        # 配置器件的初始化
        # self.set_device_cfg(deviceType=0,reg_clk_cyc=0xF,latch_clk_cyc=0xF)
        if self.init:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(FLT,command_data=CmdData(0x0FFF)),                  # 配置flt
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le1)),         # cfg_flt_le1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le2)),         # cfg_flt_le2
                CMD(CIM_RESET,command_data=CmdData(1)),                 # reset指令
                CMD(CIM_SS,command_data=CmdData(1)),                    # reg写入数据打开
                CMD(SER_PARA_SEL,command_data=CmdData(1)),              # 切换到并行模式
            ],mode=1)
            self.ps.send_packets(pkts)

            # 不为空就执行初始化
            if self.adc is not None:
                self.adc.initOp()
            if self.dac is not None:
                self.dac.initOp()

    # def set_device_cfg(self,deviceType = None,latch_cyc = None, reg_clk_cyc= None, latch_clk_cyc = None,cim_rstn_cyc = None):
    #     """
    #         设置device的cfg
    #     """
    #     self.deviceType = self.deviceType if deviceType is None else deviceType
    #     self.latch_cyc = self.latch_cyc if latch_cyc is None else latch_cyc
    #     self.reg_clk_cyc = self.reg_clk_cyc if reg_clk_cyc is None else reg_clk_cyc
    #     self.latch_clk_cyc = self.latch_clk_cyc if latch_clk_cyc is None else latch_clk_cyc
    #     self.cim_rstn_cyc = self.cim_rstn_cyc if cim_rstn_cyc is None else cim_rstn_cyc

    #     data = self.deviceType | self.latch_cyc<<1 | self. reg_clk_cyc<<3 | self.latch_clk_cyc<<7 | self.cim_rstn_cyc<<11
    #     pkts=Packet()
    #     pkts.append_cmdlist([CMD(DEVICE_CFG,command_data=CmdData(data)),],mode=1)
    #     self.ps.send_packets(pkts)

    def set_device_cfg(self,deviceType = 0):
        """
            设置device的cfg
        """
        self.deviceType = deviceType
        pkts=Packet()
        pkts.append_cmdlist([CMD(DEVICE_CFG,command_data=CmdData(self.deviceType)),],mode=1)
        self.ps.send_packets(pkts)


    def set_pulse_width(self,pulsewidth:float):
        """
            Args:
                pulsewidth: 设置cfg_row_pulse和cfg_col_pulse的脉宽
        """
        self.clk_manager.set_pulse_cyc(pulsewidth)

    def set_op_mode(self,read=True,from_row=True,clearv = True):
        """
            Args:
                read: True表示读模式, False表示写模式
                from_row: True表示从行读/写, False表示从列读/写

            Functions:
                会把所有的DAC通道电压清0
                会记录读/写模式, 从行/列进行操作\n
                会根据设置配置ROW_CTRL,COL_CTRL,ROW_COL_SW的选择
        """
        if clearv:
            self.clear_dac_v2()
        self.op_mode = "read" if read else "write"
        self.from_row = from_row
        sign = 1 if from_row else 0
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ROW_CTRL,command_data=CmdData(sign)),                                                  # 1配置行到施加电压,
            CMD(COL_CTRL,command_data=CmdData(int(not sign))),                                         # 0配置列到TIA,
            CMD(ROW_COL_SW,command_data=CmdData(sign)),                                                # 1PCB上的TIA接在列,
        ],mode=1)
        self.ps.send_packets(pkts)
        if self.deviceType == 1:
            if self.op_mode == "read":
                self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(0))])
            else:
                self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(1))])

    def send_cmd(self,cmd:list,mode:int):
        """
            Args:
                cmd: 单条上位机指令, 为一个列表
                mode: 这条指令对应的模式

            Functions:
                将指令发送出去
        """
        pkts=Packet()
        pkts.append_single(cmd,mode=mode)
        self.ps.send_packets(pkts)

    #------------------------------------------------------------------------------------------
    # ************************************** 各种索引映射 **************************************
    #------------------------------------------------------------------------------------------
    def set_cim_reset(self):
        """
            发送reset的指令
        """
        pkts=Packet()
        pkts.append_cmdlist([CMD(CIM_RESET,command_data=CmdData(0)),CMD(CIM_RESET,command_data=CmdData(1)),],mode=1)
        self.ps.send_packets(pkts)

    def numToBank_Index(self,num:int) -> tuple[int,int]:
        """
            Args:
                num: 行/列号, 从0开始

            Returns:
                tuple: (bank, index) 其中 bank 和 index 坐标从0开始
        """
        num += 1
        assert num > 0 and num < 257,"numToBank_Index: num超过范围!"
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
            bank,_ = self.numToBank_Index(i)
            bank_list[bank].append(i)
        res = []
        for i in bank_data:
            res = res + bank_list[i]
        return res
    
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
            if all_data:
                bank_data[j[2]].append(j)
            else:
                bank_data[j[2]].append(j[1])
        return [i for i in bank_data if len(i)>0]
    
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
            num = self.adc.TIA_index_map(i,device=self.deviceType,col= not row)
            tia_list[num].append(i)
        res = []
        for i in tia_data:
            res = res + tia_list[i]
        return res
    
    def tia_split(self,data:tuple[int,int,int,int,int],check_tia = True) -> list[list[tuple[int,int,int,int,int]]]:
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
                tia16[i[4]].append(i)
            # ----------------------------------------------每路TIA选一路
            flag = True
            while flag:
                flag = False
                tmp = []
                for i in tia16:
                    if len(i)>0:
                        tmp.append(i.pop())                 # 每路tia选一个值
                        flag = True
                if flag == True:
                    read_batch.append(tmp)
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
            bank_tmp,index_tmp = self.numToBank_Index(i)
            bank = bank | (1<<bank_tmp)
            index = index | (1<<index_tmp)
        return bank,index

    def get_bank_index_tia(self,num:list) -> list[tuple[int,int,int,int,int]]:
        """
            Args:
                num: 任意行/列号的列表

            Returns:
                list[tuple[int,int,int,int,int]]: 列表里面的每个数据都是对应行列号的映射结果
                为元组(pos, row_num/col_num, bank, index, tia_num)的列表
        """
        res = []
        for pos,v in enumerate(num):
            bank,index = self.numToBank_Index(v)
            tia = self.adc.TIA_index_map(v,device=self.deviceType,col=self.from_row)
            res.append((pos,v,bank,index,tia))
        return res

    def set_latch(self,num:list,row=True,value=None):
        """
            Args:
                num: 任意行/列号的列表
                value: 32bit的值或者None

            Functions:
                row为True表示行, row为False表示列
                将对应的行/列号latch配置成1
                如果value不为None,将会把这些行/列涉及的bank全配置成32bit的value值
        """
        row_col_sel = 1 if row else 0
        data = self.get_bank_index_tia(num)
        bank_data = self.bank_split(data)

        pkts=Packet()
        for i in bank_data:
            bank,index = self.get_bank_index32(i)
            index = value if value is not None else index
            pkts.append_cmdlist([
                # 行reg配置
                CMD(CIM_DATA_IN,command_data=CmdData(index)),                                       # 第index位置1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

                # 行bank配置
                CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
                CMD(CIM_BANK_SEL,command_data=CmdData(bank)),                                       # 行bank选择
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
            ],mode=1)   
        self.ps.send_packets(pkts)

    def set_bank(self,banknum:list,row=True,value=0):
        """
            Args:
                num: 任意bank号的列表
                value: 32bit的值或者None

            Functions:
                row为True表示行, row为False表示列\n
                将对应的bank号latch全配置成1\n
                如果value不为None,将会把这些行/列涉及的bank全配置成32bit的value值
        """
        assert len(banknum)>0,"set_bank: 空列表。"
        row_col_sel = 1 if row else 0

        tmp = 0
        # 配置行
        for i in banknum:
            tmp = tmp | (1<<i)
        pkts=Packet()
        pkts.append_cmdlist([
            # 行reg配置
            CMD(CIM_DATA_IN,command_data=CmdData(value)),                                       # 第xindex位置1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk
            # 行bank配置
            CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
            CMD(CIM_BANK_SEL,command_data=CmdData(tmp)),                                        # bank选择
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
        ],mode=1)   
        self.ps.send_packets(pkts)

    #------------------------------------------------------------------------------------------
    # *********************************** debug版本dac配置 *************************************
    #------------------------------------------------------------------------------------------
    def clear_dac_v(self):
        """
            Functions:
                将dac的电压全部清0
        """
        self.dac.set_voltage(0,dac_num=0,dac_channel=0)             # ROW_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=1)             # ROW_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=2)             # ROW_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=3)             # ROW_Va电压

        self.dac.set_voltage(0,dac_num=0,dac_channel=4)             # COL_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=5)             # COL_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=6)             # COL_Va电压
        self.dac.set_voltage(0,dac_num=0,dac_channel=7)             # COL_Va电压

        self.dac.set_voltage(0,dac_num=1,dac_channel=0)             # ROW_Vc
        self.dac.set_voltage(0,dac_num=1,dac_channel=1)             # COL_Vc     
        self.dac.set_voltage(0,dac_num=1,dac_channel=2)             # GL
        self.dac.set_voltage(0,dac_num=1,dac_channel=3)             # GR

    def set_dac_read_V(self,v:float,tg:float = 5):
        """
            Functions:
                设置读电压,会自动根据设定的器件类型进行设置\n
                ReRAM: 设置TG, ROW_Va和COL_Va都会设置为v\n
                ECRAM: 行读, 设置ROW_Va为v; 列读, 设置COL_Va为v
        """
        self.read_voltage = v
        if self.deviceType==0:
            if self.from_row:
                self.dac.set_voltage(tg,dac_num=0,dac_channel=6)          # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
            else:   
                self.dac.set_voltage(tg,dac_num=0,dac_channel=6)          # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
        elif self.deviceType==1:    
            # 新版1T1E需要ROW, COL的Va电压都加
            if self.from_row:  
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)             # ROW_Va电压

                self.dac.set_voltage(v,dac_num=0,dac_channel=4)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)             # COL_Va电压

    def set_dac_write_V(self,v:float,tg:float = 5):
        """
            Functions:
                设置写电压,会自动根据设定的器件类型进行设置\n
                ReRAM: 设置TG, ROW_Va和COL_Va都会设置为v\n
        """
        self.write_voltage = v
        if self.deviceType==0:
            if self.from_row:
                self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
            else:   
                self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
        elif self.deviceType==1:    
            # 写不确定怎么弄
            if self.from_row:  
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)             # ROW_Va电压
            else:
                self.dac.set_voltage(v,dac_num=0,dac_channel=4)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)             # COL_Va电压

    #------------------------------------------------------------------------------------------
    # ************************************** 读相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def set_tia_gain(self,gain:int):
        """
            Args:
                设置TIA的增益为gain
        """
        self.adc.set_gain(gain)

    def get_tia_out(self,num:list) -> np.ndarray:
        """
            Args:
                num: 包含要读取的tia号的列表

            Returns:
                np.ndarray为电压(v)
        """
        voltage = self.adc.get_out(num)
        return voltage
    
    def voltage_to_cond(self,voltage:np.ndarray,read_voltage:float = None) -> np.ndarray:
        """
            Args:
                voltage: TIA读出的电压值
                read_voltage: 读器件时用的电压值

            Returns:
                电压值对应的电导(单位:uS)
        """
        read_voltage = self.read_voltage if read_voltage is None else read_voltage
        return self.adc.voltage_to_cond(voltage=voltage,read_voltage=read_voltage)

    def voltage_to_resistance(self,voltage,read_voltage = None) -> np.ndarray:
        """
            Args:
                voltage: TIA读出的电压值
                read_voltage: 读器件时用的电压值

            Returns:
                电压值对应的电阻(单位:KΩ)
        """
        read_voltage = self.read_voltage if read_voltage is None else read_voltage
        return self.adc.voltage_to_resistance(voltage=voltage,read_voltage=read_voltage)
    
    def generate_read_pulse(self):
        """
            Functions:
                根据设定的从行/列读, 产生读脉冲的指令
                这里FPGA把行列的脉冲都连在一起了,所以去掉了翻转
                且不用主动给列脉冲
        """
        read_ins_data = FAST_COMMAND1_CONF.cfg_row_read if self.from_row else FAST_COMMAND1_CONF.cfg_col_read
        pkts=Packet()
        pkts.append_cmdlist([CMD(FAST_COMMAND_1,command_data=CmdData(read_ins_data))],mode=1)
        self.ps.send_packets(pkts)

    def read(self,row_index:list,col_index:list, 
             row_value = None, col_value = None, 
             check_tia=True) -> np.ndarray:
        """
            Args:
                row_index: 要配置的任意行索引
                col_index: 要配置的任意列索引
                row_value: 如果row_value不为None,将会把这些行涉及的bank全配置成32bit的row_value值
                col_value: 如果col_value不为None,将会把这些列涉及的bank全配置成32bit的col_value值
                check_tia: 表示是否需要处理一路TIA只能映射一列的问题

            Returns:
                np.ndarray为电压(v)
        """
        assert self.op_mode == "read","未设置为读模式。"
        assert self.read_voltage is not None,"未设置读电压。"

        if not self.from_row:
            row_index, col_index = col_index, row_index
        # ----------------------------------------------行数据映射
        row_data = self.get_bank_index_tia(row_index)
        col_data = self.get_bank_index_tia(col_index)                                                 # 映射得到i,num,bank, index, tia
        # ----------------------------------------------映射16路tia
        col_batch = self.tia_split(col_data,check_tia = check_tia)
        # ----------------------------------------------循环去读
        res = []
        for i in col_batch:
            # ------------------------------------------reset然后配置行
            self.set_cim_reset()
            self.set_latch([j[1] for j in row_data],row=self.from_row,value=row_value)
            self.set_latch([j[1] for j in i],row=not self.from_row,value=col_value)
            # ------------------------------------------给读脉冲
            self.generate_read_pulse() 
            # ------------------------------------------读出结果
            if not check_tia:
                res.append(self.adc.get_out([i for i in range(self.chip_tia_num)]))
            else:
                res.append(self.adc.get_out([j[4] for j in i]))
        if not check_tia:
            result_v = [res[i] for i in range(len(col_batch))]
        else:
            # ----------------------------------------------将结果映射回原来的顺序
            result_v = [0]*len(col_index)
            for i,v1 in enumerate(col_batch):
                # 第i个批次读, v2为(pos, row_num/col_num, bank, index, tia_num)
                for j,v2 in enumerate(v1):
                    result_v[v2[0]]=res[i][j]
        if not self.from_row:
            return np.array(result_v).T
        else:
            return np.array(result_v)

    #------------------------------------------------------------------------------------------
    # ************************************** 写相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def generate_write_pulse(self):
        """
            Functions:
                根据设定的从行/列写, 产生写脉冲的指令
                这里FPGA把行列的脉冲都连在一起了,所以去掉了翻转
                从行写只用给行脉冲, 从列写只用给列脉冲(对应方向会自动跟着给脉冲)
        """
        write_ins_data = FAST_COMMAND1_CONF.cfg_row_pulse if self.from_row else FAST_COMMAND1_CONF.cfg_col_pulse
        pkts=Packet()
        pkts.append_cmdlist([CMD(FAST_COMMAND_1,command_data=CmdData(write_ins_data))],mode=1)
        self.ps.send_packets(pkts)

    def write_one(self,row_index:int,col_index:int):
        """
            Args:
                row_index: 要配置的任意行索引
                col_index: 要配置的任意列索引

            Functions:
                写某一个器件
        """
        assert self.op_mode == "write","未设置为写模式。"
        assert self.write_voltage is not None,"未设置写电压。"

        if not self.from_row:
            row_index, col_index = col_index, row_index

        self.set_cim_reset()                                                                # 先reset 
        self.set_latch([row_index],row=self.from_row,value=None)                            # 配置行
        self.set_latch([col_index],row=not self.from_row,value=None)                        # 配置列
        self.generate_write_pulse()                                                         # 产生写脉冲

    def close(self):
        """
            Functions:
                关闭TCP连接
        """
        self.ps.close()

    #------------------------------------------------------------------------------------------
    # ************************************* 新版加速代码 ***************************************
    #------------------------------------------------------------------------------------------

    #------------------------------------------------------------------------------------------
    # *************************************** 其他操作 *****************************************
    #------------------------------------------------------------------------------------------
    def set_op_mode2(self,read=True,from_row=True,clearv = True):
        """
            Args:
                read: True配置为读模式, False配置为写模式
                from_row: True配置为从行读/写, False配置为从列读/写

            Functions:
                同时会将所有的DAC通道电压设置为0
        """
        if clearv:
            self.clear_dac_v2()
        if read:
            self.op_mode = "read"
            self.from_row = from_row
            if self.deviceType == 1:
                self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(0))])
        else:
            self.op_mode = "write"
            self.from_row = from_row
            if self.deviceType == 1:
                self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(1))])


    def execute_ins(self,ins_data:list,ins_ram_start:int):
        """
            Args:
                ins_data: 需要执行的指令的list

            Functions:
                自动检查指令长度,配置,然后执行
                并会清空指令列表
        """
        ins_num = len(ins_data)
        assert ins_num+ins_ram_start < self.ins_ram_threshold,f"execute_ins: ins_ram:{ins_num+ins_ram_start}超过界限。"
        ins_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(ins_num)))
        ins_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(ins_ram_start)))

        pkts=Packet()
        pkts.append_single(ins_data,mode=4)
        pkts.append_single([CMD(INS_NUM,command_data=CmdData(ins_num))],mode=1)
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
        self.ps.send_packets(pkts)
        # packet添加指令时都会对指令进行浅拷贝
        ins_data.clear()

    def execute_send_din_data(self,din_ram_data:list,din_ram_start:int):
        """
            Args:
                din_ram_data: 需要下发到din_ram的数据list

            Functions:
                自动检查指令长度,配置,然后执行
                并会清空数据列表
        """
        num = len(din_ram_data)
        assert num+din_ram_start <= self.din_ram_threshold,f"send_din_ram2: din_ram:{num+din_ram_start}超过界限。"
        din_ram_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(num)))                
        din_ram_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(din_ram_start)))

        pkts=Packet()
        pkts.append_single(din_ram_data,mode=5)
        self.ps.send_packets(pkts)
        # packet添加指令时都会对指令进行浅拷贝
        din_ram_data.clear()
    
    #------------------------------------------------------------------------------------------
    # *************************************** DAC配置 *****************************************
    #------------------------------------------------------------------------------------------
    def clear_dac_v2(self):
        """
            Functions:
                将16路DAC通道电压设置为0
        """
        pkts=Packet()

        cmd=[CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16)) for i in range(12)]
        num = len(cmd)
        cmd.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(num)))
        cmd.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(0)))

        pkts.append_single(cmd,mode=4)
        pkts.append_single([CMD(INS_NUM,command_data=CmdData(num))],mode=1)
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)

        self.ps.send_packets(pkts)

    def get_dac_ins2(self,v:float = None,tg:float = None):
        """
            Args:
                read: True配置为读模式, False配置为写模式
                row: True配置为从行读/写, False配置为从列读/写

            Functions:
                根据读写模式和器件要求配置对应的dac电压
        """
        cmd=[]
        if v is not None:
            if self.op_mode == "read":
                if self.deviceType==0:                      # ReRAM
                    if self.from_row:                       # 从行读
                        for i in DAC_INFO.RERAM_ROW_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
                    else:                                   # 从列读
                        for i in DAC_INFO.RERAM_COL_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
                elif self.deviceType==1:                    # ECRAM
                        for i in DAC_INFO.ECRAM_ROW_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
                        for i in DAC_INFO.ECRAM_COL_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
            elif self.op_mode == "write":
                if self.deviceType==0:                      # ReRAM
                    if self.from_row:                       # 从行写
                        for i in DAC_INFO.RERAM_ROW_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
                    else:                                   # 从列写
                        for i in DAC_INFO.RERAM_COL_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
            elif self.deviceType==1:                    # ECRAM
                    if self.from_row:                       # 从行写
                        for i in DAC_INFO.ECRAM_ROW_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
                    else:                                   # 从列写
                        for i in DAC_INFO.ECRAM_COL_VA:
                            cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
        if tg is not None:
            if self.op_mode == "read":
                if self.deviceType==0:                      # ReRAM
                    for i in DAC_INFO.RERAM_TG:
                        cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(tg))))
                elif self.deviceType==1:                    # ECRAM
                    pass
            elif self.op_mode == "write":
                if self.deviceType==0:                      # ReRAM
                    for i in DAC_INFO.RERAM_TG:
                        cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(tg))))
            elif self.deviceType==1:                    # ECRAM
                pass
        return cmd
    
    #------------------------------------------------------------------------------------------
    # ********************************* 块读写相关函数(并行) ***********************************
    #------------------------------------------------------------------------------------------
    def send_din_ram2(self,row_index_list:list[list[int]],col_index:list[int],din_ram_start=0,
                          check_tia=True) -> tuple[list[list],list[list],list[list]]:
        """
            发送配置行列latch需要的数据
            check_tia是否检查TIA的映射
        """
        
        din_ram_pos = din_ram_start
        # --------------------------------------------------准备din_ram的数据
        din_ram_data = []                                   # 要发送下去的数据
        res_row_bank = []                                   # 等会配行bank指令执行需要的数据, 双层list, 第一层list的长度表示切换一次col配置要切换几次row配置
        res_col_bank = []                                   # 等会配列bank指令执行需要的数据, 双层list, 第一层list的长度表示要切换几次col配置
        res_col_tia  = []                                   # 需要读出tia的值, 双层list
        din_ram_bank_index_map = {}                         # 用于节约din空间

        # --------------------------------------------------增加映射
        def add_map(tmp_list:list,index:list) -> None:
            """
                将对应的映射填入
            """
            nonlocal din_ram_pos
            bank32,index32 = self.get_bank_index32(index)
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                             # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            tmp_list.append((bank32,din_ram_bank_index_map[index32]))
        # --------------------------------------------------din_ram的开始存0,用于恢复 
        din_ram_data.append(CMD(PL_DATA,command_data=CmdData(0)))
        din_ram_pos = din_ram_pos+1
        # --------------------------------------------------行数据映射--------------------------------------------------
        for row_index in row_index_list:
            row_tmp = []
            row_data = self.get_bank_index_tia(row_index)
            for i in self.bank_split(row_data,all_data=False):                                          # 切分到bank进行配置
                add_map(row_tmp,i)
            res_row_bank.append(row_tmp)                                                                # 行有几个batch

        # --------------------------------------------------列数据映射--------------------------------------------------
        col_data = self.get_bank_index_tia(col_index)                                                   # (pos, row_num/col_num, bank, index, tia_num)
        if self.op_mode == "read":                                                                      # read模式按是否检查TIA来分batch
            read_batch = self.tia_split(col_data,check_tia=check_tia)
            for batch in read_batch:                                                                    # 每个batch要读哪些点
                col_tmp = []
                for bank_data in self.bank_split(batch,all_data=False):                                 # 切分到bank进行配置
                    add_map(col_tmp,bank_data)

                res_col_bank.append(col_tmp)                                                            # 这个batch要配置的bank
                res_col_tia.append([(j[0],j[4]) for j in batch] )                                       # 第j[0]个需要读的列, 第j[4]路TIA
        elif self.op_mode == "write":                                                                   # write模式必须按一列一列的来写
            for data in col_data:
                col_tmp = []
                add_map(col_tmp,[data[1]])
                res_col_bank.append(col_tmp)

        # --------------------------------------------------指令发送--------------------------------------------------
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)

        return res_row_bank,res_col_bank,res_col_tia
    
    def read2(self,row_index:list,col_index:list,read_voltage:float,tg:float = 5,
              check_tia = True,sum = True):
        """
            读器件, row_index为行索引, col_index为列索引
        """
        assert self.op_mode == "read","未设置为读模式。"
        self.read_voltage = read_voltage

        # ----------------------------------------------从行还是列去读
        if self.from_row:                                                                               # 从行读
            row_bank_ins, col_bank_ins =  PL_ROW_BANK, PL_COL_BANK
            read_ins = PL_READ_ROW_PULSE
        else:                                                                                           # 从列读
            row_index, col_index = col_index, row_index
            row_bank_ins, col_bank_ins =  PL_COL_BANK, PL_ROW_BANK
            read_ins = PL_READ_COL_PULSE

        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start

        # ----------------------------------------------发送要配置的bank的数据进去
        if sum:                                                                                         # 所有行求和
            res_row_bank,res_col_bank,res_col_tia = self.send_din_ram2([row_index],col_index,din_ram_start,check_tia)
        else:                                                                                           # 每行单独读,to do:做个优化,相同bank的行放在一起
            res_row_bank,res_col_bank,res_col_tia = self.send_din_ram2([[i] for i in row_index],col_index,din_ram_start,check_tia)

        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        
        # ----------------------------------------------记录数据映射，最后用于TIA的映射输出
        record = []
        for col_batch,col in enumerate(res_col_bank):                                                   # 因为只有16路TIA, 所以可能会有多个列的batch, 每个batch最大读16路TIA
            ins_data.append(CMD(PL_CIM_RESET))
            for bank,din_ram_pos in col:                                                                # 每个col_batch, 可能需要配置多个bank
                ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))            # 从din_ram的din_ram_pos位置取数据配置bank

            row_bank_record = [[],[]]                                                                   # 用于优化多行单独读的情况, 如果前后bank相同, 后面就不需要手动清0
            for row_pos,row in enumerate(res_row_bank):                                                 # 如果是所有行求和的情况, res_row_bank里面只会有一个元素, 每行单独读, 就是行数
                if not sum and len(row_bank_record[0])>0:                                               # 每行单独读的情况
                    for bank,din_ram_pos in row:                                                        # 得到新的行bank号
                        row_bank_record[1].append(bank)

                    for bank in row_bank_record[0]:                                                     # 如果新旧的行bank号不一样, 就手动重置一下不一样的bank
                        if bank not in row_bank_record[1]:
                            ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|0)))          # 从din_ram的0位置取32bit的0配置bank

                row_bank_record = [[],[]]

                for bank,din_ram_pos in row:                                                            # 切换row的配置
                    ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank
                    row_bank_record[0].append(bank)                                                     # 记录上一次读的行bank号

                ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))                       # 读脉冲, 并将16路TIA的值存在dout_ram的dout_ram_pos位置
                record.append((col_batch,row_pos))                                                      # 记录是读列的几个batch, 是第几行, 读出的数据存在哪
                dout_ram_pos = dout_ram_pos + 1

        num = len(ins_data)                                                                             # 指令长度
        assert num+ins_ram_start < self.ins_ram_threshold,f"read2: ins_ram:{num+ins_ram_start}超过界限。"
        assert dout_ram_pos <= self.dout_ram_threshold,f"read2: dout_ram:{dout_ram_pos}超过界限。"
        ins_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(num)))                                # 告诉上面要执行多少指令
        ins_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(ins_ram_start)))                         # 告诉上面指令放在哪

        # ----------------------------------------------发送指令序列并执行
        pkts=Packet()
        pkts.append_single(ins_data,mode=4)
        pkts.append_single([CMD(INS_NUM,command_data=CmdData(num))],mode=1)
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
        self.ps.send_packets(pkts)

        voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
        
        # voltage = np.array([[j for i in range(16)] for j in range(dout_ram_pos)])
        # cond = np.array([[j for i in range(16)] for j in range(dout_ram_pos)])
        if not check_tia:
            return voltage                                # 直接返回16路TIA的值
        else:
            row_len = 1 if sum else len(row_index)
            vres = np.zeros((row_len,len(col_index)))
            # 每个record对应一个dout_ram_pos,并且是按顺序的
            for i,(col_batch,row_pos) in enumerate(record):
                # 遍历这个batch对应的列和tia
                for col_pos,tia_num in res_col_tia[col_batch]:
                    vres[row_pos,col_pos]=voltage[i, tia_num]
            if self.from_row:
                return vres
            else:
                # 从列读,需要转置一次
                return vres.T
    
    def read_crossbar2(self,row_index:list,col_index:list,read_voltage:float,tg:float = 5,gain:int = 1,
                       from_row:bool = True,out_type:int = 0):
        """
            out_type: 0为电压, 1为电导(uS), 2为电阻(KΩ)
        """
        assert out_type >= 0 and out_type <=2, "read_crossbar2: 返回类型错误。"
        assert len(row_index)>0, "read_crossbar2: row_index不能为空"
        assert len(col_index)>0, "read_crossbar2: col_index不能为空"
        self.set_tia_gain(gain=gain)
        self.set_op_mode2(read=True,from_row=from_row)
        

        resv = np.zeros((len(row_index),len(col_index)))
        if from_row:
            row_data = self.get_bank_index_tia(num = row_index)
            row_bank_data = self.bank_split(data = row_data,all_data = True)                # (pos, row_num/col_num, bank, index, tia_num)
            for bank_data in row_bank_data:                                                 # 因为下位机TCP容量限制, 从行读, 每次最多4行, 切分到同一个bank会减少切bank的次数
                chunks = [bank_data[i:i+4] for i in range(0, len(bank_data), 4)]
                for chunk in chunks:
                    vres0 = self.read2(row_index=[i[1] for i in chunk],col_index=col_index,read_voltage=read_voltage,tg=tg,check_tia=True,sum=False)
                    for k,v in enumerate(chunk): resv[v[0],:]=vres0[k,:]                    # 行索引
        else:
            col_data = self.get_bank_index_tia(num = col_index)
            col_bank_data = self.bank_split(data = col_data,all_data = True)                # (pos, row_num/col_num, bank, index, tia_num)
            for bank_data in col_bank_data:                                                 # 因为下位机TCP容量限制, 从列读, 每次最多4列, 切分到同一个bank会减少切bank的次数
                chunks = [bank_data[i:i+4] for i in range(0, len(bank_data), 4)]        
                for chunk in chunks:
                    vres0 = self.read2(row_index=row_index,col_index=[i[1] for i in chunk],read_voltage=read_voltage,tg=tg,check_tia=True,sum=False)
                    for k,v in enumerate(chunk): resv[:,v[0]]=vres0[:,k]                    # 列索引

        if out_type == 0:
            return resv
        elif out_type == 1:
            return self.voltage_to_cond(voltage=resv, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=resv, read_voltage=read_voltage)
    
    #------------------------------------------------------------------------------------------
    # ************************************** 写相关操作 ****************************************
    #------------------------------------------------------------------------------------------    
    def write2(self,row_index:list,col_index:list,write_voltage:float,tg:float = 5):
        """
            写器件, row_index为行索引, col_index为列索引
        """
        assert self.op_mode == "write","未设置为写模式。"
        self.write_voltage = write_voltage
        # ----------------------------------------------从行还是列去写
        if self.from_row:                                                                               # 从行写
            write_ins = PL_WRITE_ROW_PULSE
        else:                                                                                           # 从列写
            write_ins = PL_WRITE_COL_PULSE

        # 哪个短, 放在前面固定, 切bank次数会更少
        if len(col_index)<len(row_index):
            row_bank_ins, col_bank_ins =  PL_ROW_BANK, PL_COL_BANK
        else:
            row_index, col_index = col_index, row_index
            row_bank_ins, col_bank_ins =  PL_COL_BANK, PL_ROW_BANK

        # ----------------------------------------------ins_ram,din_ram的地址
        ins_ram_start = 0
        din_ram_start = 0

        # ----------------------------------------------发送要配置的bank的数据进去
        res_row_bank,res_col_bank,_ = self.send_din_ram2([[i] for i in row_index],col_index,din_ram_start,False)

        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=write_voltage,tg=tg)                                             # 配置电压

        row_bank_record = [[],[]]                                                                       # 用于优化多行单独写的情况, 如果前后bank相同, 后面就不需要手动清0
        col_bank_record = [[],[]]                                                                       # 0号是旧的, 1号是新的
        ins_data.append(CMD(PL_CIM_RESET))

        for col_batch,col in enumerate(res_col_bank): 
            # ----------------------------------------------------------------------------------
            if len(col_bank_record[0])>0:                                                           # 每列单独写的情况
                for bank,din_ram_pos in col:                                                        # 得到新的列bank号
                    col_bank_record[1].append(bank)

                for bank in col_bank_record[0]:                                                     # 如果新旧的列bank号不一样, 就手动重置一下不一样的bank
                    if bank not in col_bank_record[1]:
                        ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|0)))          # 从din_ram的0位置取32bit的0配置bank
            col_bank_record = [[],[]]
            for bank,din_ram_pos in col:
                ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank
                col_bank_record[0].append(bank)  

            # ----------------------------------------------------------------------------------
            for row_pos,row in enumerate(res_row_bank):                                             # res_row_bank里面只会有一个元素, 每行单独写, 就是行数
                if len(row_bank_record[0])>0:                                                       # 每行单独写的情况
                    for bank,din_ram_pos in row:                                                    # 得到新的行bank号
                        row_bank_record[1].append(bank)

                    for bank in row_bank_record[0]:                                                 # 如果新旧的行bank号不一样, 就手动重置一下不一样的bank
                        if bank not in row_bank_record[1]:
                            ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|0)))      # 从din_ram的0位置取32bit的0配置bank
                row_bank_record = [[],[]]

                for bank,din_ram_pos in row:                                                        # 切换row的配置
                    ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))    # 从din_ram的din_ram_pos位置取数据配置bank
                    row_bank_record[0].append(bank)                                                 # 记录上一次写的行bank号

                ins_data.append(CMD(write_ins))                                                     # 写脉冲

        self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

    def write_crossbar2(self,row_index:list,col_index:list,write_voltage:float,tg:float,pulse_width:float,
                       set_device:bool = True):
        assert len(row_index)>0, "read_crossbar2: row_index不能为空"
        assert len(col_index)>0, "read_crossbar2: col_index不能为空"
        self.set_op_mode2(read=False,from_row=set_device)
        self.set_pulse_width(pulse_width)
        # 现在由于容量限制,每次最多写128个器件,切分到同一个bank会减少切bank的次数
        if len(row_index)<len(col_index):
            col_data = self.get_bank_index_tia(num = col_index)
            col_bank_data = self.bank_split(data = col_data,all_data = False)
            chunk0,chunk1 = [],[]

            for bank_data in col_bank_data:
                if len(chunk0+bank_data)<=128:
                    chunk0 = chunk0 + bank_data 
                else:
                    chunk1 = chunk1 + bank_data
            for i in row_index:
                if len(chunk0)>0:
                    self.write2(row_index=[i],col_index=chunk0,write_voltage=write_voltage,tg=tg)
                if len(chunk1)>0:
                    self.write2(row_index=[i],col_index=chunk1,write_voltage=write_voltage,tg=tg)
        else:
            row_data = self.get_bank_index_tia(num = row_index)
            row_bank_data = self.bank_split(data = row_data,all_data = False)                # (pos, row_num/col_num, bank, index, tia_num)
            chunk0,chunk1 = [],[]

            for bank_data in row_bank_data:
                if len(chunk0+bank_data)<=128:
                    chunk0 = chunk0 + bank_data 
                else:
                    chunk1 = chunk1 + bank_data
            for i in col_index:
                if len(chunk0)>0:
                    self.write2(row_index=chunk0,col_index=[i],write_voltage=write_voltage,tg=tg)
                if len(chunk1)>0:
                    self.write2(row_index=chunk1,col_index=[i],write_voltage=write_voltage,tg=tg)

    #------------------------------------------------------------------------------------------
    # ******************************** 点读写相关操作(非并行) **********************************
    #------------------------------------------------------------------------------------------    
    def send_point_din_ram2(self,points:list[tuple[int,int]],din_ram_start:int = 0,) -> tuple[list[tuple[int,int]],list[tuple[int,int]],list[int]]:
        """
            Args:
                points: 需要配置的点的数据, 行列数据
                din_ram_start: 下发数据的din_ram的起始地址,默认为0

            Returns:
                res_row_bank: 一个个点需要配置的行bank和din_ram_data里面的index的映射\n
                res_col_bank: 一个个点需要配置的列bank和din_ram_data里面的index的映射\n
                res_tia_map: 每个点的TIA映射(写模式返回为空)
        """

        # --------------------------------------------------准备din_ram的数据
        din_ram_pos = din_ram_start+1                                                                   # 因为32bit的0在din_ram_data里面, 所以需要+1
        din_ram_data = [CMD(PL_DATA,command_data=CmdData(0))]                                           # 要发送下去的数据, din_ram的开始存0,用于恢复
        res_row_bank = []                                                                               # 等会配行bank指令执行需要的数据, 单层list
        res_col_bank = []                                                                               # 等会配列bank指令执行需要的数据, 单层list
        res_tia_map  = []                                                                               # 每个点对应的TIA映射,需要提前选好从行列读, 单层list
        din_ram_bank_index_map = {}                                                                     # 用于节约din空间

        # --------------------------------------------------增加映射
        def add_map(res_bank:list,index:int) -> None:                                                   # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank32,index32 = self.get_bank_index32([index])
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank32,din_ram_bank_index_map[index32]))

        for row,col in points:
            add_map(res_row_bank,row)
            add_map(res_col_bank,col)
            if self.op_mode == "read":
                if self.from_row:
                    res_tia_map.append(self.adc.TIA_index_map(index = col,device = self.deviceType,col = True))
                else:
                    res_tia_map.append(self.adc.TIA_index_map(index = row,device = self.deviceType,col = False))
                
        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        return res_row_bank,res_col_bank,res_tia_map
        
    def read_point2(self,crossbar:np.ndarray,read_voltage:float,tg:float = 5,gain:int = 1,from_row:bool = True, out_type = 0):
        """
            读器件, row_index为行索引, col_index为列索引
        """
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)

        # --------------------------------------------------配置写的点的数据, 因为行/列对应的bank是间隔1, 所以为了避免更多的切行列bank, 尽量使得一个bank的挨在一起
        # crossbar为0时, if会自动转成False
        row,col = crossbar.shape
        points = []
        for i_start in range(2):
            for i in range(i_start,row,2):
                points += [(i,j) for j in range(0,col,2) if crossbar[i,j]] + [(i,j) for j in range(1,col,2) if crossbar[i,j]]

        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        read_ins = PL_READ_ROW_PULSE if from_row else PL_READ_COL_PULSE
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start
        res_row_bank,res_col_bank,res_tia_map = self.send_point_din_ram2(points,din_ram_start)

        res = np.zeros((row,col))
        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        
        row_bank_data_last, col_bank_data_last = (0,0),(0,0)
        point_nums = len(res_row_bank)
        print(f"需要读{point_nums}个点")
        last_point_pos = 0
        for k in range(point_nums):
            # 是否需要清空原来的bank
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                ins_data.append( CMD(PL_CIM_RESET) )
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                ins_data.append( CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k]:
                ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))

            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]

            ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))
            dout_ram_pos += 1
            
            # 检测是否超过阈值, 超过就先执行命令
            if len(ins_data) >= self.ins_ram_threshold-5 or dout_ram_pos >= self.dout_ram_threshold:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(last_point_pos,k+1):
                    res[points[i]] = voltage[i-last_point_pos,res_tia_map[i]]
                dout_ram_pos = dout_ram_start
                last_point_pos = k+1

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
            for i in range(last_point_pos,point_nums):
                res[points[i]] = voltage[i-last_point_pos,res_tia_map[i]]

        if out_type == 0:
            return res
        elif out_type == 1:
            return self.voltage_to_cond(voltage=res, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)
        
            
    def write_point2(self,crossbar:np.ndarray,write_voltage:float,tg:Union[float|np.ndarray],pulse_width:float,set_device:bool = True):
        
        self.write_voltage = write_voltage
        self.set_op_mode2(read=False,from_row=set_device)
        self.set_pulse_width(pulse_width)

        # --------------------------------------------------配置写的点的数据, 因为行/列对应的bank是间隔1, 所以为了避免更多的切行列bank, 尽量使得一个bank的挨在一起
        # crossbar为0时, if会自动转成False
        row,col = crossbar.shape
        points = []
        for i_start in range(2):
            for i in range(i_start,row,2):
                points += [(i,j) for j in range(0,col,2) if crossbar[i,j]] + [(i,j) for j in range(1,col,2) if crossbar[i,j]]

        # ----------------------------------------------ins_ram,din_ram的地址
        write_ins = PL_WRITE_ROW_PULSE if set_device else PL_WRITE_COL_PULSE
        ins_ram_start = 0
        din_ram_start = 0

        res_row_bank,res_col_bank,_ = self.send_point_din_ram2(points,din_ram_start = din_ram_start)
        # ----------------------------------------------准备指令序列
        change_tg = type(tg)==np.ndarray
        ins_data = self.get_dac_ins2(v=write_voltage,tg=None if change_tg else tg)                                             # 配置电压

        row_bank_data_last, col_bank_data_last = (0,0),(0,0)
        v_last = 0
        point_nums = len(res_row_bank)
        print(f"需要写{point_nums}个点")
        for k in range(point_nums):
            # 是否需要清空原来的bank
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                ins_data.append( CMD(PL_CIM_RESET) )
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                ins_data.append( CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k]:
                ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))

            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]
            # 改变tg的电压
            if change_tg:
                tg_v = tg[points[k][0],points[k][1]]
                if tg_v!=v_last:
                    ins_data +=self.get_dac_ins2(tg=tg_v)
                    v_last = tg_v
            # 写指令
            ins_data.append(CMD(write_ins))
            
            if len(ins_data) >= self.ins_ram_threshold-5:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)












































    # def write2(self,row_index:list,col_index:list,write_voltage:float,tg:float = 5):
    #     """
    #         写器件, row_index为行索引, col_index为列索引
    #     """
    #     assert self.op_mode == "write","未设置为写模式。"
    #     self.write_voltage = write_voltage
    #     # ----------------------------------------------从行还是列去写
    #     if self.from_row:                                                                               # 从行写
    #         write_ins = PL_WRITE_ROW_PULSE
    #     else:                                                                                           # 从列写
    #         row_index, col_index = col_index, row_index
    #         row_bank_ins, col_bank_ins =  PL_COL_BANK, PL_ROW_BANK
    #         write_ins = PL_WRITE_COL_PULSE

    #     # ----------------------------------------------ins_ram,din_ram的地址
    #     ins_ram_start = 0
    #     din_ram_start = 0

    #     # ----------------------------------------------发送要配置的bank的数据进去
    #     res_row_bank,res_col_bank,_ = self.send_din_ram2([[i] for i in row_index],col_index,din_ram_start,False)

    #     # ----------------------------------------------准备指令序列
    #     ins_data = self.get_dac_ins2(v=write_voltage,tg=tg)                                             # 配置电压

    #     row_bank_record = [[],[]]                                                                       # 用于优化多行单独写的情况, 如果前后bank相同, 后面就不需要手动清0
    #     col_bank_record = [[],[]]                                                                       # 0号是旧的, 1号是新的
    #     ins_data.append(CMD(PL_CIM_RESET))

    #     # 哪个短就把哪个放在固定的一方
    #     if len(col_index)<len(row_index):                                                               # 哪个短, 放在前面固定, 切bank次数会更少
    #         for col_batch,col in enumerate(res_col_bank): 
    #             # ----------------------------------------------------------------------------------
    #             if len(col_bank_record[0])>0:                                                           # 每列单独写的情况
    #                 for bank,din_ram_pos in col:                                                        # 得到新的列bank号
    #                     col_bank_record[1].append(bank)

    #                 for bank in col_bank_record[0]:                                                     # 如果新旧的列bank号不一样, 就手动重置一下不一样的bank
    #                     if bank not in col_bank_record[1]:
    #                         ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|0)))          # 从din_ram的0位置取32bit的0配置bank
    #             col_bank_record = [[],[]]
    #             for bank,din_ram_pos in col:
    #                 ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank
    #                 col_bank_record[0].append(bank)  

    #             # ----------------------------------------------------------------------------------
    #             for row_pos,row in enumerate(res_row_bank):                                             # res_row_bank里面只会有一个元素, 每行单独写, 就是行数
                    
    #                 if len(row_bank_record[0])>0:                                                       # 每行单独写的情况
    #                     for bank,din_ram_pos in row:                                                    # 得到新的行bank号
    #                         row_bank_record[1].append(bank)

    #                     for bank in row_bank_record[0]:                                                 # 如果新旧的行bank号不一样, 就手动重置一下不一样的bank
    #                         if bank not in row_bank_record[1]:
    #                             ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|0)))      # 从din_ram的0位置取32bit的0配置bank
    #                 row_bank_record = [[],[]]

    #                 for bank,din_ram_pos in row:                                                        # 切换row的配置
    #                     ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))    # 从din_ram的din_ram_pos位置取数据配置bank
    #                     row_bank_record[0].append(bank)                                                 # 记录上一次写的行bank号

    #                 ins_data.append(CMD(write_ins))                                                     # 写脉冲
    #     else:
    #         for row_pos,row in enumerate(res_row_bank):                                                 # res_row_bank里面只会有一个元素, 每行单独写, 就是行数
    #             # ----------------------------------------------------------------------------------
    #             if len(row_bank_record[0])>0:                                                           # 每行单独写的情况
    #                 for bank,din_ram_pos in row:                                                        # 得到新的行bank号
    #                     row_bank_record[1].append(bank)

    #                 for bank in row_bank_record[0]:                                                     # 如果新旧的行bank号不一样, 就手动重置一下不一样的bank
    #                     if bank not in row_bank_record[1]:
    #                         ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|0)))          # 从din_ram的0位置取32bit的0配置bank
    #             row_bank_record = [[],[]]

    #             for bank,din_ram_pos in row:                                                            # 切换row的配置
    #                 ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank
    #                 row_bank_record[0].append(bank)                                                     # 记录上一次写的行bank号

    #             # ----------------------------------------------------------------------------------
    #             for col_batch,col in enumerate(res_col_bank): 
    #                 if len(col_bank_record[0])>0:                                                       # 每列单独写的情况
    #                     for bank,din_ram_pos in col:                                                    # 得到新的列bank号
    #                         col_bank_record[1].append(bank)

    #                     for bank in col_bank_record[0]:                                                 # 如果新旧的列bank号不一样, 就手动重置一下不一样的bank
    #                         if bank not in col_bank_record[1]:
    #                             ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|0)))      # 从din_ram的0位置取32bit的0配置bank
    #                 col_bank_record = [[],[]]

    #                 for bank,din_ram_pos in col:
    #                     ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))    # 从din_ram的din_ram_pos位置取数据配置bank
    #                     col_bank_record[0].append(bank)   
                        
    #                 ins_data.append(CMD(write_ins))                                                     # 写脉冲

    #     num = len(ins_data)
    #     assert num+ins_ram_start < self.ins_ram_threshold,f"write2: ins_ram:{num+ins_ram_start}超过界限。"
    #     ins_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(num)))
    #     ins_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(ins_ram_start)))

    #     # ----------------------------------------------发送指令序列并执行
    #     pkts=Packet()
    #     pkts.append_single(ins_data,mode=4)
    #     pkts.append_single([CMD(INS_NUM,command_data=CmdData(num))],mode=1)
    #     pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
    #     self.ps.send_packets(pkts)