from command import CMD,CmdData,Packet
from command.singleCmdInfo import *
from compiler import COMPILER,SIMULATOR

from pc import PS
from modules.adc import ADC
from modules.dac import DAC
from modules.clkManager import CLK_MANAGER
from modules.compensation import COMPENSATION
from compiler.chipSetting import CHIPSETTING

import itertools
import numpy as np
import time
import os

from typing import List, Union

class CHIP():
    """
        对chip进行的操作
    """
    chip_sel = 0                    # 选择18个阵列中的一个

    op_mode = None                  # 当前所处模式
    from_row = True                 # 从行/列读写
    read_voltage = None             # 读写电压
    write_voltage = None            # 写电压

    ps:PS = None
    adc:ADC = None
    dac:DAC = None
    clk_manager:CLK_MANAGER = None
    setting:CHIPSETTING = None
    compensation:COMPENSATION = None

    compilers = None

    init = True

    read_parallel2_data = None

    need_reset = False               # 两个芯片同用需要reset另一个芯片

    def __init__(self, ps:PS,deviceType:int = 0,IsNew32:bool=False,IsRERAM512:bool=False,init = True):
        self.ps = ps
        self.init = init
        self.setting = CHIPSETTING(deviceType=deviceType,IsNew32=IsNew32,IsRERAM512=IsRERAM512)
        self.initOp()
        self.adc = ADC(ps,self.setting,init)
        self.dac = DAC(ps,self.setting,init)
        self.clk_manager = CLK_MANAGER(ps,init)
        self.compensation = COMPENSATION()
        
        self.compilers = {}

    def add_compiler(self,directory:str,encoding:str = 'utf-8'):
        """
            增加汇编代码
        """
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.txt'):
                    self.compilers[file] = COMPILER()
                    self.compilers[file].load_assembler_ins(os.path.join(root, file),encoding)

    def get_compiler(self,name:str)->COMPILER:
        """
            获取汇编代码
        """
        res = self.compilers.get(name,None)
        if res is None:
            raise Exception(f"汇编文件{name}没找到。")
        return res

    def get_setting_info(self):
        """
            输出相关信息
        """
        device = "ECRAM" if self.setting.deviceType else "ReRAM"
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

    def set_device_cfg(self,deviceType:int = 0,IsNew32:bool=False,IsRERAM512:bool=False):
        """
            设置device的cfg
        """
        pkts=Packet()
        pkts.append_cmdlist([CMD(DEVICE_CFG,command_data=CmdData(deviceType)),],mode=1)
        self.ps.send_packets(pkts)
        self.setting.set_device(deviceType=deviceType,IsNew32=IsNew32,IsRERAM512=IsRERAM512)


    def set_pulse_width(self,pulsewidth:float):
        """
            Args:
                pulsewidth: 设置cfg_row_pulse和cfg_col_pulse的脉宽
        """
        self.clk_manager.set_pulse_cyc(pulsewidth)

    def set_op_mode(self,read=True,from_row=True):
        """
            Args:
                read: True表示读模式, False表示写模式
                from_row: True表示从行读/写, False表示从列读/写

            Functions:
                会把所有的DAC通道电压清0
                会记录读/写模式, 从行/列进行操作\n
                会根据设置配置ROW_CTRL,COL_CTRL,ROW_COL_SW的选择
        """
        if (read and self.op_mode != "read") or (not read and self.op_mode == "read"):
            self.clear_dac_v()
        self.op_mode = "read" if read else "write"
        self.from_row = from_row
        pkts=Packet()
        if self.setting.deviceType == 1:
            self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(self.op_mode != "read"))],mode=1)
            if self.op_mode=="write":
                pkts.append_cmdlist([
                    CMD(ROW_CTRL,command_data=CmdData(1)),                                                  # 1配置行到施加电压,
                    CMD(COL_CTRL,command_data=CmdData(not from_row)),                                                  # 0配置列到TIA,
                    CMD(ROW_COL_SW,command_data=CmdData(from_row)),                                             # 1PCB上的TIA接在列,
                ],mode=1)
            else:
                pkts.append_cmdlist([
                    CMD(ROW_CTRL,command_data=CmdData(from_row)),                                                  # 1配置行到施加电压,
                    CMD(COL_CTRL,command_data=CmdData(not from_row)),                                                  # 0配置列到TIA,
                    CMD(ROW_COL_SW,command_data=CmdData(from_row)),                                             # 1PCB上的TIA接在列,
                ],mode=1)
        else:
            if self.setting.IsRERAM512:
                pkts.append_cmdlist([
                    CMD(ROW_COL_SW,command_data=CmdData(from_row)),                                                # 1PCB上的TIA接在列,
                ],mode=1)
            else:
                pkts.append_cmdlist([
                    CMD(ROW_CTRL,command_data=CmdData(from_row)),                                                  # 1配置行到施加电压,
                    CMD(COL_CTRL,command_data=CmdData(not from_row)),                                         # 0配置列到TIA,
                    CMD(ROW_COL_SW,command_data=CmdData(from_row)),                                                # 1PCB上的TIA接在列,
                ],mode=1)

        self.ps.send_packets(pkts)

    def set_cim_reset(self):
        """
            发送reset的指令
        """
        pkts=Packet()
        if self.setting.IsRERAM512:
            pkts.append_cmdlist([CMD(COL_CTRL,command_data=CmdData(0)),CMD(COL_CTRL,command_data=CmdData(1)),],mode=1)
            pkts.append_cmdlist([CMD(CIM_RESET,command_data=CmdData(0)),
                                 CMD(CIM_RESET,command_data=CmdData(1)),
                                 CMD(CIM_RESET,command_data=CmdData(0))],mode=1)
        else:
            pkts.append_cmdlist([CMD(CIM_RESET,command_data=CmdData(0)),CMD(CIM_RESET,command_data=CmdData(1)),],mode=1)
        self.ps.send_packets(pkts)   

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
        data = self.setting.get_bank_index_tia(num,self.from_row)
        bank_data = self.setting.bank_split(data)

        pkts=Packet()
        for i in bank_data:
            bank,index = self.setting.get_bank_index32(i)
            # print("配置",bank,hex(index))
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
            # 行bank配置
            CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
            CMD(CIM_BANK_SEL,command_data=CmdData(tmp)),                                        # bank选择
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
            # 行reg配置
            CMD(CIM_DATA_IN,command_data=CmdData(value)),                                       # 第xindex位置1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

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
        if self.setting.deviceType==0:
            if self.setting.IsRERAM512:
                # print("配置电压")
                self.dac.set_voltage(tg,dac_num=1,dac_channel=0)            # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=3)             # ROW_Va
            else:
                if self.from_row:
                    self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                    self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                else:   
                    self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                    self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
        elif self.setting.deviceType==1:    
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
        if self.setting.deviceType==0:
            if self.setting.IsRERAM512:
                self.dac.set_voltage(tg,dac_num=1,dac_channel=0)            # TG
                self.dac.set_voltage(v,dac_num=1,dac_channel=3)             # ROW_Va
            else:
                if self.from_row:
                    self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                    self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                else:   
                    self.dac.set_voltage(tg,dac_num=0,dac_channel=6)            # TG
                    self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
        elif self.setting.deviceType==1:    
            if self.from_row:     
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # GL
                self.dac.set_voltage(v,dac_num=1,dac_channel=3)             # GR
            else:
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)             # ROW_Va电压

                self.dac.set_voltage(v,dac_num=0,dac_channel=4)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)             # COL_Va电压

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Vc
                self.dac.set_voltage(v,dac_num=1,dac_channel=1)             # COL_Vc     
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # GL
                self.dac.set_voltage(v,dac_num=1,dac_channel=3)             # GR

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
        row_data = self.setting.get_bank_index_tia(row_index,self.from_row)
        col_data = self.setting.get_bank_index_tia(col_index,self.from_row)                                                 # 映射得到i,num,bank, index, tia
        # ----------------------------------------------映射16路tia
        col_batch = self.setting.tia_split(col_data,check_tia = check_tia)
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
                res.append(self.adc.get_out([i for i in range(self.setting.chip_tia_num)]))
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

    def write_ecram_one(self,row,col,v,pulse_width,isSet=True):
        self.set_op_mode(read=False,from_row=isSet)
        self.set_dac_read_V(v)
        self.set_pulse_width(pulsewidth=pulse_width)
        self.set_cim_reset()
        if isSet:
            self.set_latch([row],row=True,value=None)
            self.set_latch([col],row=False,value=None)
        else:
            bank,index = self.setting.numToBank_Index(row)
            self.set_bank([i for i in range(8)],row=True,value=0xFFFF_FFFF)
            self.set_bank([bank],row=True,value=0xFFFF_FFFF^(1<<index))
            self.set_latch([col],row=False,value=None)

        self.generate_write_pulse()


    def read_ecram_one(self,row:list,col:int,v,from_row=True):
        self.set_op_mode(read=True,from_row=from_row)
        self.set_dac_write_V(v)
        self.set_cim_reset()

        self.set_latch(row,row=True,value=None)
        self.set_bank([i for i in range(8)],row=False,value=0xFFFF_FFFF)

        # -----------------------------------------------------------------
        row_col_sel = 0
        data = self.setting.get_bank_index_tia([col],self.from_row)
        bank_data = self.setting.bank_split(data)

        pkts=Packet()
        for i in bank_data:
            bank,index = self.setting.get_bank_index32(i)
            if index&0xFFFF:
                index = 0xFFFF_0000 | index
            else:
                index = 0xFFFF | index
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
        # -----------------------------------------------------------------
        tia=self.setting.TIA_index_map(num=col,col=True)
        self.generate_read_pulse()
        voltage = self.get_tia_out([tia])
        return voltage

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
    def set_op_mode2(self,read=True,from_row=True):
        """
            Args:
                read: True配置为读模式, False配置为写模式
                from_row: True配置为从行读/写, False配置为从列读/写

            Functions:
                如果模式和上次不一样,会将所有的DAC通道电压设置为0
        """
        if (read and self.op_mode != "read") or (not read and self.op_mode == "read"):
            self.clear_dac_v2()
        self.from_row = from_row
        self.op_mode = "read" if read else "write"
        ins_data=[]
        if self.setting.deviceType == 1:
            self.send_cmd(cmd=[CMD(SER_DATA,command_data=CmdData(self.op_mode != "read"))],mode=1)
            if self.op_mode == "write":
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(1<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
            else:
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(int(from_row)<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
        else:
            if self.setting.IsRERAM512:
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))
            else:
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(int(from_row)<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
        self.execute_ins(ins_data=ins_data,ins_ram_start=0)

    def execute_ins(self,ins_data:list[CMD],ins_ram_start:int,message_check:str="cc550000"):
        """
            Args:
                ins_data: 需要执行的指令的list

            Functions:
                自动检查指令长度,配置,然后执行
                并会清空指令列表
        """
        if len(ins_data)==0 or ins_data[-1].command_name != "pl_exit":
            ins_data.append(CMD(PL_EXIT))
        ins_num = len(ins_data)
        assert ins_num+ins_ram_start < self.setting.ins_ram_length,f"execute_ins: ins_ram:{ins_num+ins_ram_start}超过界限。"
        ins_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(ins_num)))
        ins_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(ins_ram_start)))

        pkts=Packet()
        pkts.append_single(ins_data,mode=4)
        self.ps.send_packets(pkts)
        # pkts.append_single([CMD(INS_NUM,command_data=CmdData(ins_num))],mode=1)
        pkts=Packet()
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
        self.ps.send_packets(pkts,message_check=message_check)
        # packet添加指令时都会对指令进行浅拷贝
        ins_data.clear()

    def execute(self,message_check:str="cc550000"):
        pkts=Packet()
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
        self.ps.send_packets(pkts,message_check=message_check)

    def execute_send_din_data(self,din_ram_data:list,din_ram_start:int):
        """
            Args:
                din_ram_data: 需要下发到din_ram的数据list

            Functions:
                自动检查指令长度,配置,然后执行
                并会清空数据列表
        """
        num = len(din_ram_data)
        assert num+din_ram_start <= self.setting.din_ram_length,f"send_din_ram2: din_ram:{num+din_ram_start}超过界限。"
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
                将12路DAC通道电压设置为0
        """
        ins_data=[CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16)) for i in range(12)]
        self.execute_ins(ins_data=ins_data,ins_ram_start=0)

    def get_dac_ins2(self,v:float = None,tg:float = None)->list[CMD]:
        """
            Args:
                read: True配置为读模式, False配置为写模式
                row: True配置为从行读/写, False配置为从列读/写

            Functions:
                根据读写模式和器件要求配置对应的dac电压
        """
        cmd=[]
        dac_v = []
        
        if v is not None:
            v16 = self.dac.VToBytes(v)
            if self.op_mode == "read":
                if self.setting.deviceType==0:                      # ReRAM
                    if self.setting.IsRERAM512:
                        for i in DAC_INFO.RERAM512_VIN: dac_v.append((i,v16))
                    else:
                        if self.from_row:                       # 从行读
                            for i in DAC_INFO.RERAM_ROW_VA: dac_v.append((i,v16))
                        else:                                   # 从列读
                            for i in DAC_INFO.RERAM_COL_VA: dac_v.append((i,v16))
                elif self.setting.deviceType==1:                    # ECRAM
                        for i in DAC_INFO.ECRAM_ROW_VA: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_COL_VA: dac_v.append((i,v16))
            elif self.op_mode == "write":
                if self.setting.deviceType==0:                      # ReRAM
                    if self.setting.IsRERAM512:
                        for i in DAC_INFO.RERAM512_VIN: dac_v.append((i,v16))
                    else:
                        if self.from_row:                       # 从行读
                            for i in DAC_INFO.RERAM_ROW_VA: dac_v.append((i,v16))
                        else:                                   # 从列读
                            for i in DAC_INFO.RERAM_COL_VA: dac_v.append((i,v16))
                elif self.setting.deviceType==1:                    # ECRAM
                    if self.from_row:                       # 从行写
                        for i in DAC_INFO.ECRAM_GL: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_GR: dac_v.append((i,v16))
                    else:                                   # 从列写
                        for i in DAC_INFO.ECRAM_ROW_VA: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_COL_VA: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_ROW_VC: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_COL_VC: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_GL: dac_v.append((i,v16))
                        for i in DAC_INFO.ECRAM_GR: dac_v.append((i,v16))
        if tg is not None:
            tg16 = self.dac.VToBytes(tg)
            if self.op_mode == "read":
                if self.setting.deviceType==0:                      # ReRAM
                    if self.setting.IsRERAM512:
                        for i in DAC_INFO.RERAM512_TG:dac_v.append((i,tg16))
                    else:
                        for i in DAC_INFO.RERAM_TG: dac_v.append((i,tg16))
                elif self.setting.deviceType==1:                    # ECRAM
                    pass
            elif self.op_mode == "write":
                if self.setting.deviceType==0:                      # ReRAM
                    if self.setting.IsRERAM512:
                        for i in DAC_INFO.RERAM512_TG:dac_v.append((i,tg16))
                    else:
                        for i in DAC_INFO.RERAM_TG: dac_v.append((i,tg16))
                elif self.setting.deviceType==1:                    # ECRAM
                    pass

        for dac_data in dac_v:
            cmd.append(CMD(PL_DAC_V,command_data=CmdData((dac_data[0])<<16 | dac_data[1])))
                
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
            bank32,index32 = self.setting.get_bank_index32(index)
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
            row_data = self.setting.get_bank_index_tia(row_index,self.from_row)
            for i in self.setting.bank_split(row_data,all_data=False):                                          # 切分到bank进行配置
                add_map(row_tmp,i)
            res_row_bank.append(row_tmp)                                                                # 行有几个batch

        # --------------------------------------------------列数据映射--------------------------------------------------
        col_data = self.setting.get_bank_index_tia(col_index,self.from_row)                                                   # (pos, row_num/col_num, bank, index, tia_num)
        if self.op_mode == "read":                                                                      # read模式按是否检查TIA来分batch
            read_batch = self.setting.tia_split(col_data,check_tia=check_tia)
            for batch in read_batch:                                                                    # 每个batch要读哪些点
                col_tmp = []
                for bank_data in self.setting.bank_split(batch,all_data=False):                                 # 切分到bank进行配置
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
        assert False,"此函数已经废弃!"
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
            if self.setting.IsRERAM512:
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
            else:
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

        assert dout_ram_pos <= self.setting.dout_ram_length,f"read2: dout_ram:{dout_ram_pos}超过界限。"
        self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

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
        assert False,"此函数已经废弃!"
        assert out_type >= 0 and out_type <=2, "read_crossbar2: 返回类型错误。"
        assert len(row_index)>0, "read_crossbar2: row_index不能为空"
        assert len(col_index)>0, "read_crossbar2: col_index不能为空"
        self.set_tia_gain(gain=gain)
        self.set_op_mode2(read=True,from_row=from_row)
        

        resv = np.zeros((len(row_index),len(col_index)))
        if from_row:
            row_data = self.setting.get_bank_index_tia(row_index,self.from_row)
            row_bank_data = self.setting.bank_split(data = row_data,all_data = True)                # (pos, row_num/col_num, bank, index, tia_num)
            for bank_data in row_bank_data:                                                 # 因为下位机TCP容量限制, 从行读, 每次最多4行, 切分到同一个bank会减少切bank的次数
                chunks = [bank_data[i:i+4] for i in range(0, len(bank_data), 4)]
                for chunk in chunks:
                    vres0 = self.read2(row_index=[i[1] for i in chunk],col_index=col_index,read_voltage=read_voltage,tg=tg,check_tia=True,sum=False)
                    for k,v in enumerate(chunk): resv[v[0],:]=vres0[k,:]                    # 行索引
        else:
            col_data = self.setting.get_bank_index_tia(col_index,self.from_row)
            col_bank_data = self.setting.bank_split(data = col_data,all_data = True)                # (pos, row_num/col_num, bank, index, tia_num)
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
        assert False,"此函数已经废弃!"
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
        if self.setting.IsRERAM512:
            ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
            ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
        else:
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
        assert False,"此函数已经废弃!"
        assert len(row_index)>0, "read_crossbar2: row_index不能为空"
        assert len(col_index)>0, "read_crossbar2: col_index不能为空"
        self.set_op_mode2(read=False,from_row=set_device)
        self.set_pulse_width(pulse_width)
        # 现在由于容量限制,每次最多写128个器件,切分到同一个bank会减少切bank的次数
        if len(row_index)<len(col_index):
            col_data = self.setting.get_bank_index_tia(col_index,self.from_row)
            col_bank_data = self.setting.bank_split(data = col_data,all_data = False)
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
            row_data = self.setting.get_bank_index_tia(row_index,self.from_row)
            row_bank_data = self.setting.bank_split(data = row_data,all_data = False)                # (pos, row_num/col_num, bank, index, tia_num)
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
    # ********************************* 块读写相关函数(并行) ***********************************
    #------------------------------------------------------------------------------------------
    def get_crossbar_data(self,crossbar:np.ndarray,sum_row:bool = True) -> tuple[list[list[int]],list[list[int]]]:
        """
            行全配置,或者列全配置
        """
        row_index,col_index = [],[]
        if sum_row:
            for j in range(0,crossbar.shape[1],2):
                rows = np.where(crossbar[:, j])[0].tolist()
                if rows:
                    row_index.append(rows)
                    col_index.append([j])
            for j in range(1,crossbar.shape[1],2):
                rows = np.where(crossbar[:, j])[0].tolist()
                if rows:
                    row_index.append(rows)
                    col_index.append([j])
        else:
            for i in range(0,crossbar.shape[0],2):
                cols = np.where(crossbar[i, :])[0].tolist()
                if cols:
                    row_index.append([i])
                    col_index.append(cols)
            for i in range(1,crossbar.shape[0],2):
                cols = np.where(crossbar[i, :])[0].tolist()
                if cols:
                    row_index.append([i])
                    col_index.append(cols)
        return row_index,col_index
    
    def send_parallel_read_din_ram2(self,row_index:list[list[int]],col_index:list[list[int]],
                            tia_split:Union[list[list[int]|None]]=None,
                            check_tia:bool=True,
                            din_ram_start:int = 0) -> tuple[list[list],list[list],list]:
        """
            Args:
                row_index: 需要配置的行的数据
                col_index: 需要配置的列的数据
                din_ram_start: 下发数据的din_ram的起始地址,默认为0

            Returns:
                res_row_bank: 一个个点需要配置的行bank和din_ram_data里面的index的映射\n
                res_col_bank: 一个个点需要配置的列bank和din_ram_data里面的index的映射\n
                res_tia_map: 每个点的TIA映射(写模式返回为空)
            
            只允许读函数中使用
        """
        assert self.op_mode == "read","只允许读函数中使用。"
        # --------------------------------------------------准备din_ram的数据
        din_ram_pos = din_ram_start+1                                                                   # 因为32bit的0在din_ram_data里面, 所以需要+1
        din_ram_data = [CMD(PL_DATA,command_data=CmdData(0))]                                           # 要发送下去的数据, din_ram的开始存0,用于恢复
        res_row_bank = []                                                                               # 等会配行bank指令执行需要的数据
        res_col_bank = []                                                                               # 等会配列bank指令执行需要的数据
        res_tia_map  = []                                                                               # 每个点对应的TIA映射,需要提前选好从行列读
        din_ram_bank_index_map = {}                                                                     # 用于节约din空间

        # --------------------------------------------------增加映射
        def add_map(res_bank:list,index:list) -> None:                                                  # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank32,index32 = self.setting.get_bank_index32(index)
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank32,din_ram_bank_index_map[index32]))


        for i in range(len(row_index)):
            row_bank_data = self.setting.get_bank_index_tia(row_index[i],self.from_row)
            row_read_batch = self.setting.tia_split(row_bank_data,tia_split=tia_split,check_tia=not self.from_row and check_tia)
            col_bank_data = self.setting.get_bank_index_tia(col_index[i],self.from_row)
            col_read_batch = self.setting.tia_split(col_bank_data,tia_split=tia_split,check_tia=self.from_row and check_tia)
            
            row_read_batch = row_read_batch*len(col_read_batch)
            col_read_batch = col_read_batch*len(row_read_batch)

            for row_batch,col_batch in zip(row_read_batch,col_read_batch):
                res_row_bank.append([])
                res_col_bank.append([])
                for rows in self.setting.bank_split(row_batch,all_data=False):
                    add_map(res_row_bank[-1],rows)
                for cols in self.setting.bank_split(col_batch,all_data=False):
                    add_map(res_col_bank[-1],cols)

                # 每个batch都会读一次#(pos, row_num/col_num, bank, index, tia_num)# 行号,列号,tia_num
                if self.from_row:
                    res_tia_map.append([(row_batch[0][1],j[1],j[4]) for j in col_batch])
                else:
                    res_tia_map.append([(j[1],col_batch[0][1],j[4]) for j in row_batch])

        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        return res_row_bank,res_col_bank,res_tia_map
    
    def read_parallel2(self,crossbar:np.ndarray,read_voltage:float,tg:float = 5,
                       gain:int = 1,from_row:bool = True, out_type = 0,
                       tia_split:Union[list[list[int]|None]]=None,use_last_data:bool=False):
        """
            读器件, row_index为行索引, col_index为列索引
        """
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)

        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        read_ins = PL_READ_ROW_PULSE if from_row else PL_READ_COL_PULSE
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start
        # --------------------------------------------------配置写的点的数据, 因为行/列对应的bank是间隔1, 所以为了避免更多的切行列bank, 尽量使得一个bank的挨在一起
        row,col = crossbar.shape
        if use_last_data:
            res_row_bank,res_col_bank,res_tia_map = self.read_parallel2_data
        else:
            row_index,col_index = self.get_crossbar_data(crossbar,sum_row=not from_row)
            res_row_bank,res_col_bank,res_tia_map = self.send_parallel_read_din_ram2(row_index,col_index,tia_split,True,din_ram_start)
            self.read_parallel2_data = (res_row_bank,res_col_bank,res_tia_map)

        res = np.zeros((row,col))
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        read_nums = 0
        read_batch_start,read_batch_end = 0,0

        row_banks_last,col_banks_last = [],[]
        row_bank_num_last,col_bank_num_last = [],[]
        for row_banks,col_banks in zip(res_row_bank,res_col_bank):
            add_ins_data = []
            row_bank_num_new,col_bank_num_new = [row_bank[0] for row_bank in row_banks],[col_bank[0] for col_bank in col_banks]
            if row_bank_num_new==row_bank_num_last and col_bank_num_new==col_bank_num_last:
                if row_banks_last!=row_banks:
                    for row_bank in row_banks:
                        add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank[0]<<8|row_bank[1])))  # 配置行bank

                if col_banks_last!=col_banks:
                    for col_bank in col_banks:
                        add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(col_bank[0]<<8|col_bank[1])))  # 配置列bank
            else:
                if self.setting.IsRERAM512:
                    add_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                    add_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
                else:
                    add_ins_data.append( CMD(PL_CIM_RESET))
                for row_bank in row_banks:
                    add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank[0]<<8|row_bank[1])))  # 配置行bank
                for col_bank in col_banks:
                    add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(col_bank[0]<<8|col_bank[1])))  # 配置列bank

            add_ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))

            row_banks_last,col_banks_last = row_banks,col_banks
            row_bank_num_last,col_bank_num_last = row_bank_num_new,col_bank_num_new
            
            if len(ins_data)+len(add_ins_data)+1 >= self.setting.ins_ram_length or dout_ram_pos+1 >= self.setting.dout_ram_length:
                read_nums+=1
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(read_batch_start,read_batch_end):
                    for row,col,tia in res_tia_map[i]:
                        res[row,col]=voltage[i-read_batch_start,tia]
                
                read_batch_start = read_batch_end

                dout_ram_pos = dout_ram_start
                add_ins_data[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data += add_ins_data
            dout_ram_pos += 1
            read_batch_end +=1

        if len(ins_data)>0:
            read_nums+=1
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
            for i in range(read_batch_start,read_batch_end):
                for row,col,tia in res_tia_map[i]:
                    res[row,col]=voltage[i-read_batch_start,tia]

        #print(f"共发送指令{read_nums}次")
        if out_type == 0:
            return res
        elif out_type == 1:
            return self.voltage_to_cond(voltage=res, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)

    def send_parallel_chunk_read_din_ram2(self,row_index:list[list[int]],col_index:list[list[int]],
                            tia_split:Union[list[list[int]|None]]=None,
                            din_ram_start:int = 0) -> tuple[list[list],list[list],list]:
        """
            Args:
                row_index: 需要配置的行的数据
                col_index: 需要配置的列的数据
                din_ram_start: 下发数据的din_ram的起始地址,默认为0

            Returns:
                res_row_bank: 一个个点需要配置的行bank和din_ram_data里面的index的映射\n
                res_col_bank: 一个个点需要配置的列bank和din_ram_data里面的index的映射\n
                res_tia_map: 每个点的TIA映射(写模式返回为空)
            
            只允许读函数中使用
        """
        assert self.op_mode == "read","只允许读函数中使用。"
        # --------------------------------------------------准备din_ram的数据
        din_ram_pos = din_ram_start+1                                                                   # 因为32bit的0在din_ram_data里面, 所以需要+1
        din_ram_data = [CMD(PL_DATA,command_data=CmdData(0))]                                           # 要发送下去的数据, din_ram的开始存0,用于恢复
        res_row_bank = []                                                                               # 等会配行bank指令执行需要的数据
        res_col_bank = []                                                                               # 等会配列bank指令执行需要的数据
        res_tia_map  = []                                                                               # 每个点对应的TIA映射,需要提前选好从行列读
        din_ram_bank_index_map = {}                                                                     # 用于节约din空间

        # --------------------------------------------------增加映射
        def add_map(res_bank:list,index:list) -> None:                                                  # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank32,index32 = self.setting.get_bank_index32(index)
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank32,din_ram_bank_index_map[index32]))

        if self.from_row:
            col_bank_data = self.setting.get_bank_index_tia(col_index[0],self.from_row)
            col_read_batch = self.setting.tia_split(col_bank_data,tia_split=tia_split,check_tia=True)

            row_bank_data = [self.setting.bank_split(self.setting.get_bank_index_tia(i,self.from_row),all_data=False) for i in row_index]
            for col_batch in col_read_batch:
                # 每个列batch遍历多行
                cols_bank = self.setting.bank_split(col_batch,all_data=False)
                for row_num,rows_bank in enumerate(row_bank_data):
                    res_row_bank.append([])
                    res_col_bank.append([])
                    for rows in rows_bank:
                        add_map(res_row_bank[-1],rows)
                    for cols in cols_bank:
                        add_map(res_col_bank[-1],cols)
                    res_tia_map.append([(row_index[row_num][0],j[1],j[4]) for j in col_batch])
        else:
            row_bank_data = self.setting.get_bank_index_tia(row_index[0],self.from_row)
            row_read_batch = self.setting.tia_split(row_bank_data,tia_split=tia_split,check_tia=True)

            col_bank_data = [self.setting.bank_split(self.setting.get_bank_index_tia(i,self.from_row),all_data=False) for i in col_index]
            for row_batch in row_read_batch:
                # 每个行latch遍历多列
                rows_bank = self.setting.bank_split(row_batch,all_data=False)
                for col_num,cols_bank in enumerate(col_bank_data):
                    res_row_bank.append([])
                    res_col_bank.append([])
                    for rows in rows_bank:
                        add_map(res_row_bank[-1],rows)
                    for cols in cols_bank:
                        add_map(res_col_bank[-1],cols)
                    res_tia_map.append([(j[1],col_index[col_num][0],j[4]) for j in row_batch])

        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        return res_row_bank,res_col_bank,res_tia_map
    
    def read_chunk_parallel2(self,row_num_start:int=0,row_num_end:int=256,col_num_start:int=0,col_num_end:int=256,
                            row_index:list[list[int]]=None, col_index:list[list[int]]= None,
                            read_voltage:float=0.1,tg:float = 5,
                            gain:int = 1,from_row:bool = True, out_type = 0,
                            compute:bool = False,
                            tia_split:Union[list[list[int]|None]]=None,use_last_data:bool=False):
        """
            左闭右开区间[row_num_start,row_num_end)
            如果没有给出row_index和col_index,那么会使用row_num_start和row_num_end限定区域自动生成
            如果不是进行推理,只是单纯并行读,
            从行给信号,row_index形式为[[行0],[行2],[行3]...],col_index形式为[[所有列号(会自动切分tia的batch)]]
            如果是进行推理,
            从行给信号读的话,row_index形式为[[所有行的行号]],col_index形式为[[所有列号(会自动切分tia的batch)]]
        """
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)

        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        read_ins = PL_READ_ROW_PULSE if from_row else PL_READ_COL_PULSE
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start
        # --------------------------------------------------配置写的点的数据, 因为行/列对应的bank是间隔1, 所以为了避免更多的切行列bank, 尽量使得一个bank的挨在一起
        row,col = row_num_end-row_num_start,col_num_end-col_num_start
        if use_last_data:
            res_row_bank,res_col_bank,res_tia_map = self.read_parallel2_data
        else:
            if from_row:
                if row_index is None:
                    row_index = [list(range(row_num_start,row_num_end))] if compute else[[i] for i in range(row_num_start,row_num_end,2)]+[[i] for i in range(row_num_start+1,row_num_end,2)]
                if col_index is None:
                    col_index = [[i for i in range(col_num_start,col_num_end,2)]+[i for i in range(col_num_start+1,col_num_end,2)]]
            else:
                if row_index is None:
                    row_index = [[i for i in range(row_num_start,row_num_end,2)]+[i for i in range(row_num_start+1,row_num_end,2)]]
                if col_index is None:
                    col_index = [list(range(col_num_start,col_num_end))] if compute else [[i] for i in range(col_num_start,col_num_end,2)]+[[i] for i in range(col_num_start+1,col_num_end,2)]
            res_row_bank,res_col_bank,res_tia_map = self.send_parallel_chunk_read_din_ram2(row_index,col_index,tia_split,din_ram_start)
            self.read_parallel2_data = (res_row_bank,res_col_bank,res_tia_map)

        if compute:
            res = np.zeros((1,col)) if from_row else np.zeros((row,1))
        else:
            res = np.zeros((row,col))
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        read_nums = 0
        read_batch_start,read_batch_end = 0,0

        row_banks_last,col_banks_last = [],[]
        row_bank_num_last,col_bank_num_last = [],[]
        for row_banks,col_banks in zip(res_row_bank,res_col_bank):
            add_ins_data = []
            row_bank_num_new,col_bank_num_new = [row_bank[0] for row_bank in row_banks],[col_bank[0] for col_bank in col_banks]
            if row_bank_num_new==row_bank_num_last and col_bank_num_new==col_bank_num_last:
                if row_banks_last!=row_banks:
                    for row_bank in row_banks:
                        add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank[0]<<8|row_bank[1])))  # 配置行bank

                if col_banks_last!=col_banks:
                    for col_bank in col_banks:
                        add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(col_bank[0]<<8|col_bank[1])))  # 配置列bank
            else:
                if self.setting.IsRERAM512:
                    add_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                    add_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
                else:
                    add_ins_data.append( CMD(PL_CIM_RESET))
                for row_bank in row_banks:
                    add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank[0]<<8|row_bank[1])))  # 配置行bank
                for col_bank in col_banks:
                    add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(col_bank[0]<<8|col_bank[1])))  # 配置列bank

            add_ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))

            row_banks_last,col_banks_last = row_banks,col_banks
            row_bank_num_last,col_bank_num_last = row_bank_num_new,col_bank_num_new
            
            if len(ins_data)+len(add_ins_data)+1 >= self.setting.ins_ram_length or dout_ram_pos+1 >= self.setting.dout_ram_length:
                read_nums+=1
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(read_batch_start,read_batch_end):
                    for row,col,tia in res_tia_map[i]:
                        if compute:
                            if from_row:
                                res[0,col-col_num_start] = voltage[i-read_batch_start,tia]
                            else:
                                res[row-row_num_start,0] = voltage[i-read_batch_start,tia]
                        else:
                            res[row-row_num_start,col-col_num_start]=voltage[i-read_batch_start,tia]
                
                read_batch_start = read_batch_end

                dout_ram_pos = dout_ram_start
                add_ins_data[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data += add_ins_data
            dout_ram_pos += 1
            read_batch_end +=1

        if len(ins_data)>0:
            read_nums+=1
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
            for i in range(read_batch_start,read_batch_end):
                for row,col,tia in res_tia_map[i]:
                    if compute:
                        if from_row:
                            res[0,col-col_num_start] = voltage[i-read_batch_start,tia]
                        else:
                            res[row-row_num_start,0] = voltage[i-read_batch_start,tia]
                    else:
                        res[row-row_num_start,col-col_num_start]=voltage[i-read_batch_start,tia]

        #(f"共发送指令{read_nums}次")
        if out_type == 0:
            return res
        elif out_type == 1:
            return self.voltage_to_cond(voltage=res, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)
        
    #------------------------------------------------------------------------------------------
    # ******************************** 点读写相关操作(非并行) **********************************
    #------------------------------------------------------------------------------------------ 

    def send_point_din_ram2(self,points:list[tuple[int,int]],din_ram_start:int = 0,inversion_type:int=0
                            ) -> tuple[list[tuple[int,int]],list[tuple[int,int]],list[int]]:
        """
            Args:
                points: 需要配置的点的数据, 行列数据
                din_ram_start: 下发数据的din_ram的起始地址,默认为0
                inversion_type: 用于ECRAM的兼容
                    =0,表示不使用反转
                    =1,表示全部反转
                    =2,表示只反转对应行/列所在TIA之外的所有索引

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
        if inversion_type>0:
            din_ram_pos = din_ram_pos+1
            din_ram_data.append(CMD(PL_DATA,command_data=CmdData(0xFFFF_FFFF)))
        # --------------------------------------------------增加映射
        def add_map(res_bank:list,index:int,inversion_type:int=0) -> None:                              # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank32,index32 = self.setting.get_bank_index32([index])
            # ------------------------------------------------------------------------------------------# ECRAM特定修改
            if inversion_type>0:
                if inversion_type == 1:                                                                 # ECRAM的行配置需要取反
                    index32 = 0xFFFF_FFFF ^ index32
                elif inversion_type == 2:
                    if index32&0xFFFF >0:
                        index32 = index32 | 0xFFFF_0000
                    else:
                        index32 = index32 | 0x0000_FFFF
            # ------------------------------------------------------------------------------------------# ECRAM特定修改
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank32,din_ram_bank_index_map[index32]))

        for row,col in points:
            if self.op_mode == "read":
                if self.from_row:
                    add_map(res_row_bank,row)
                    add_map(res_col_bank,col,inversion_type)
                    res_tia_map.append(self.setting.TIA_index_map(num = col,col = True))
                else:
                    add_map(res_row_bank,row,inversion_type)
                    add_map(res_col_bank,col)
                    res_tia_map.append(self.setting.TIA_index_map(num = row,col = False))
            else:
                add_map(res_row_bank,row,inversion_type)
                add_map(res_col_bank,col)
                
        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        return res_row_bank,res_col_bank,res_tia_map
        
    def read_point2_tia4gnd(self,crossbar:np.ndarray,read_voltage:float,tg:float = 5,gain:int = 1,from_row:bool = True, out_type = 0):
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
        res_row_bank,res_col_bank,res_tia_map = self.send_point_din_ram2(points,din_ram_start,inversion_type=2)

        res = np.zeros((row,col))
        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        
        row_bank_data_last, col_bank_data_last = (-1,-1),(-1,-1)
        point_nums = len(res_row_bank)

        last_point_pos = 0
        for k in range(point_nums):
            tmp_ins_data = []
            # 是否需要清空原来的bank
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                tmp_ins_data.append(CMD(PL_CIM_RESET))
                # 从行读，就把列全配1，从列读，就把行全配1
                if from_row:
                    tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(0xFF<<8|1)))
                else:
                    tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|1)))
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                # 从行读，就把行对应bank清零，否则全部置1
                if from_row:
                    tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
                else:
                    tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|1)))
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                # 从行读，就把对应列的bank置1，否则清零
                if from_row:
                    tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(0xFF<<8|1)))
                else:
                    tmp_ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
                

            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k][0]:
                tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))

            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]

            tmp_ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))
            
            # 检测是否超过阈值, 超过就先执行命令
            if len(ins_data) +len(tmp_ins_data)>= self.setting.ins_ram_length-2 or dout_ram_pos >= self.setting.dout_ram_length:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(last_point_pos,k):
                    res[points[i]] = voltage[i-last_point_pos,res_tia_map[i]]


                last_point_pos = k
                dout_ram_pos = dout_ram_start
                tmp_ins_data[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data += tmp_ins_data
            dout_ram_pos += 1

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
        
        row_bank_data_last, col_bank_data_last = (-1,-1),(-1,-1)
        point_nums = len(res_row_bank)
        # print(f"需要读{point_nums}个点")
        last_point_pos = 0
        for k in range(point_nums):
            tmp_ins_data = []
            # 是否需要清空原来的bank
            if self.need_reset:
                tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
            # print((row_bank_data_last[0] != res_row_bank[k][0]),(col_bank_data_last[0] != res_col_bank[k][0]))
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                if self.setting.IsRERAM512:
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
                else:
                    tmp_ins_data.append(CMD(PL_CIM_RESET))
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                tmp_ins_data.append( CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                tmp_ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k]:
                tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))

            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]
            if self.need_reset:
                if not from_row:
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))   

            tmp_ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))
            
            # 检测是否超过阈值, 超过就先执行命令
            if len(ins_data) +len(tmp_ins_data)>= self.setting.ins_ram_length-2 or dout_ram_pos >= self.setting.dout_ram_length:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(last_point_pos,k):
                    res[points[i]] = voltage[i-last_point_pos,res_tia_map[i]]


                last_point_pos = k
                dout_ram_pos = dout_ram_start
                tmp_ins_data[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data += tmp_ins_data
            dout_ram_pos += 1

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

    def write_point2_ecram(self,crossbar:np.ndarray,write_voltage:float,pulse_width:float,set_device:bool = True):

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

        res_row_bank,res_col_bank,_ = self.send_point_din_ram2(points,din_ram_start = din_ram_start,inversion_type=int(not set_device))
        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=write_voltage,tg=None)                                               # 配置电压
        row_bank_data_last, col_bank_data_last = (-1,-1),(-1,-1)
        point_nums = len(res_row_bank)
        # print(f"需要写{point_nums}个点")
        for k in range(point_nums):
            tmp_ins_data = []
            # 是否需要清空原来的bank
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                tmp_ins_data.append(CMD(PL_CIM_RESET))
                if not set_device:
                    tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|1)))
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                if not set_device:
                    tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|1)))
                else:
                    tmp_ins_data.append( CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                tmp_ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k][0]:
                tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))


            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]

            tmp_ins_data.append(CMD(write_ins))
            if len(ins_data)+len(tmp_ins_data) >= self.setting.ins_ram_length-2:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

            ins_data += tmp_ins_data

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

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

        row_bank_data_last, col_bank_data_last = (-1,-1),(-1,-1)
        v_last = 0
        point_nums = len(res_row_bank)
        # print(f"需要写{point_nums}个点")
        for k in range(point_nums):
            tmp_ins_data = []
            if self.need_reset:
                tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
            # 是否需要清空原来的bank
            if (row_bank_data_last[0] != res_row_bank[k][0]) and (col_bank_data_last[0] != res_col_bank[k][0]):
                if self.setting.IsRERAM512:
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
                else:
                    tmp_ins_data.append(CMD(PL_CIM_RESET))
            elif row_bank_data_last[0] != res_row_bank[k][0]:
                tmp_ins_data.append( CMD(PL_ROW_BANK,command_data=CmdData(row_bank_data_last[0]<<8|0)) )
            elif col_bank_data_last[0] != res_col_bank[k][0]:
                tmp_ins_data.append( CMD(PL_COL_BANK,command_data=CmdData(col_bank_data_last[0]<<8|0)) )
            # 是否需要重新配置bank
            if row_bank_data_last!=res_row_bank[k]:
                tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][0]<<8|res_row_bank[k][1])))
            if col_bank_data_last!=res_col_bank[k]:
                tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][0]<<8|res_col_bank[k][1])))

            if self.need_reset:
                if not set_device:
                    tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))  

            row_bank_data_last,col_bank_data_last = res_row_bank[k],res_col_bank[k]
            # 改变tg的电压
            if change_tg:
                tg_v = tg[points[k][0],points[k][1]]
                if tg_v!=v_last:
                    tmp_ins_data +=self.get_dac_ins2(tg=tg_v)
                    v_last = tg_v
            # 写指令
            tmp_ins_data.append(CMD(write_ins))
            
            if len(ins_data)+len(tmp_ins_data) >= self.setting.ins_ram_length-2:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

            ins_data += tmp_ins_data

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)

    #------------------------------------------------------------------------------------------
    # ************************************ 选多行单列(读写) ************************************
    #------------------------------------------------------------------------------------------
    def send_compute_din_ram2(self,row_index:list[list[int]],col_index:list[list[int]],
                              din_ram_start:int = 0) -> tuple[list[list[tuple[int,int]]],list[list[tuple[int,int]]],list[int]]:
        """
            Args:
                row_index: 需要配置的行的数据
                col_index: 需要配置的列的数据
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
        def add_map(res_bank:list,index:list) -> None:                                                  # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank32,index32 = self.setting.get_bank_index32(index)
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank32,din_ram_bank_index_map[index32]))

        for row_data in row_index:
            row_bank_data = self.setting.get_bank_index_tia(row_data,self.from_row)
            row_bank = self.setting.bank_split(row_bank_data,all_data=False)
            res_row_bank.append([])
            for rows in row_bank:
                add_map(res_row_bank[-1],rows)

        for col_data in col_index:
            col_bank_data = self.setting.get_bank_index_tia(col_data,self.from_row)
            col_bank = self.setting.bank_split(col_bank_data,all_data=False)
            res_col_bank.append([])
            for cols in col_bank:
                add_map(res_col_bank[-1],cols)

        if self.op_mode == "read":
            if self.from_row:
                res_tia_map.extend(self.setting.TIA_index_map(num=col, col=True) for col_data in col_index for col in col_data)
            else:
                res_tia_map.extend(self.setting.TIA_index_map(num=row, col=False) for row_data in row_index for row in row_data)
                
        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        return res_row_bank,res_col_bank,res_tia_map

    def compute(self,crossbar:np.ndarray,read_voltage:float,tg:float = 5,gain:int = 1,from_row:bool = True, out_type = 0):
        """
            并行推理
            从行给信号进行推理时,每次推理一列,这一列里面可以开启任意行(选中的行会全打开)
            
        """
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)

        # --------------------------------------------------配置写的点的数据, 因为行/列对应的bank是间隔1, 所以为了避免更多的切行列bank, 尽量使得一个bank的挨在一起
        row,col = crossbar.shape
        row_index,col_index = self.get_crossbar_data(crossbar,sum_row=from_row)
        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        read_ins = PL_READ_ROW_PULSE if from_row else PL_READ_COL_PULSE
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start
        res_row_bank,res_col_bank,res_tia_map = self.send_compute_din_ram2(row_index,col_index,din_ram_start)

        res = np.zeros((1,col)) if from_row else np.zeros((row,1))
        res_tmp = []
        # ----------------------------------------------准备指令序列
        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)                                              # 得到配置电压的指令序列
        cal_nums = len(res_tia_map)
        # row_bank_data_last, col_bank_data_last = (0,0),(0,0)
        #print(f"需要计算{cal_nums}次")
        last_point_pos = 0
        for k in range(cal_nums):
            tmp_ins_data = []
            if self.setting.IsRERAM512:
                tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(0<<16)))
                tmp_ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(1<<16)))
            else:
                tmp_ins_data.append(CMD(PL_CIM_RESET))

            for i in range(len(res_row_bank[k])):
                tmp_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(res_row_bank[k][i][0]<<8|res_row_bank[k][i][1])))  # 配置行bank
            
            for i in range(len(res_col_bank[k])):
                tmp_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(res_col_bank[k][i][0]<<8|res_col_bank[k][i][1])))  # 配置列bank

            tmp_ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))

            # 检测是否超过阈值, 超过就先执行命令
            # print("命令",len(ins_data)+len(tmp_ins_data))
            if len(ins_data)+len(tmp_ins_data) >= self.setting.ins_ram_length-5 or dout_ram_pos+1 >= self.setting.dout_ram_length:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(last_point_pos,k):
                    res_tmp.append(voltage[i-last_point_pos,res_tia_map[i]])
                dout_ram_pos = dout_ram_start
                last_point_pos = k

                tmp_ins_data[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data += tmp_ins_data
            dout_ram_pos += 1
            
        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
            for i in range(last_point_pos,cal_nums):
                res_tmp.append(voltage[i-last_point_pos,res_tia_map[i]])

        for k in range(cal_nums):
            if from_row:
                res[0,col_index[k][0]] = res_tmp[k]
            else:
                res[row_index[k][0],0] = res_tmp[k]

        if out_type == 0:
            return res
        elif out_type == 1:
            return self.voltage_to_cond(voltage=res, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)

    #------------------------------------------------------------------------------------------
    # *************************************** 汇编执行 ***************************************
    #------------------------------------------------------------------------------------------
    def send_din_ram3(self,row_num_start:int,row_num_end:int,col_num_start:int,col_num_end:int,
                      din_ram_start:int = 0,) -> tuple[dict,list[int],list[int]]:
        """
            Args:
                row_num_start: 行号左边界
                row_num_end: 行号右边界
                col_num_start: 列号左边界
                col_num_end: 列号右边界
                din_ram_start: din_ram起始地址

            Returns:
                res: 汇编代码中需要预先获取的常量值
                row_data: 按顺序遍历的行bank数据
                col_data: 按顺序遍历的列bank数据
        """
        res = dict(
            row_bank_din_ram_s_c = 0,                                                                   # 要读的行bank号存放的位置,以及右边界
            row_bank_din_ram_e_c = 0,
            col_bank_din_ram_s_c = 8,                                                                   # 要读的列bank号存放的位置,以及右边界
            col_bank_din_ram_e_c = 8,
            row_index_din_ram_s_c = 16,                                                                  # 每个行bank的起始index号和结束index号存放的位置
            row_index_din_ram_e_c = 24,
            col_index_din_ram_s_c = 32,                                                                  # 每个列bank的起始index号和结束index号存放的位置
            col_index_din_ram_e_c = 40,
        )

        # --------------------------------------------------准备din_ram的数据
        din_ram_data = [CMD(PL_DATA,command_data=CmdData(0)) for i in range(48)]                        # 要发送下去的数据, din_ram的开始存0,用于恢复

        # --------------------------------------------------处理行bank
        row_data = self.setting.get_bank_index_tia(list(range(row_num_start,row_num_end)),self.from_row)
        row_data = self.setting.bank_split(row_data,all_data=True)
        i=0
        for i,v in enumerate(row_data):
            # (pos, row_num/col_num, bank, index, tia_num)
            din_ram_data[res["row_bank_din_ram_s_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[0][2]))
            din_ram_data[res["row_index_din_ram_s_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[0][3]))
            din_ram_data[res["row_index_din_ram_e_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[-1][3]))
        res["row_bank_din_ram_e_c"] = res["row_bank_din_ram_s_c"]+i

        # --------------------------------------------------处理列bank
        col_data = self.setting.get_bank_index_tia(list(range(col_num_start,col_num_end)),self.from_row)
        col_data = self.setting.bank_split(col_data,all_data=True)
        i=0
        for i,v in enumerate(col_data):
            # (pos, row_num/col_num, bank, index, tia_num)
            din_ram_data[res["col_bank_din_ram_s_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[0][2]))
            din_ram_data[res["col_index_din_ram_s_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[0][3]))
            din_ram_data[res["col_index_din_ram_e_c"]+i]=CMD(PL_DATA,command_data=CmdData(v[-1][3]))
        res["col_bank_din_ram_e_c"] = res["col_bank_din_ram_s_c"] +i

        # --------------------------------------------------发送数据
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)
        
        row_data = [j[0] for i in row_data for j in i]
        col_data = [j[0] for i in col_data for j in i]
        return res,row_data,col_data
    
    def read_point3(self,row_num_start:int,row_num_end:int,col_num_start:int,col_num_end:int,
                    read_voltage:float,tg:float = 5,gain:int = 1,from_row:bool = True, out_type = 0,):
        """
            Args:
                row_num_start: 行号左边界
                row_num_end: 行号右边界
                col_num_start: 列号左边界
                col_num_end: 列号右边界

            Returns:
                对应块大小的矩阵
            
                左闭右开
        """
        assert row_num_start>=0 and row_num_start<256 and row_num_end>=0 and row_num_end<=256, "超过界限"
        assert col_num_start>=0 and col_num_start<256 and col_num_end>=0 and col_num_end<=256, "超过界限"
        if row_num_start>=row_num_end or col_num_start>=col_num_end:
            # print("0个点需要读。")
            return np.array([])
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)
        if from_row:
            compiler = self.get_compiler("read_point3_from_row.txt")
        else:
            compiler = self.get_compiler("read_point3_from_col.txt")

        din_ram_start = 0
        ins_ram_start = 0
        count_max_c = self.setting.dout_ram_length
        const_data,row_data,col_data = self.send_din_ram3(row_num_start,row_num_end,col_num_start,col_num_end,din_ram_start)

        for k,v in const_data.items():
            compiler.add_const_variable(k,v)

        compiler.add_const_variable("count_max_c",count_max_c)
        compiler.add_const_variable("pq_c",1)

        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)
        compiler.add_offset(len(ins_data))
        ins_data = ins_data + compiler.get_ins_data()

        self.execute_ins(ins_data=ins_data,ins_ram_start = ins_ram_start,message_check=None)

        # 等待读取数据
        row_length = row_num_end-row_num_start
        col_length = col_num_end-col_num_start
        res = np.zeros((row_length,col_length))

        point_num = row_length*col_length
        num_max = count_max_c*16
        num = num_max
        
        voltage = None
        flag=False
        for row_pos in row_data:
            for col_pos in col_data:
                if num == num_max:
                    voltage,flag = self.adc.get_out3(min(point_num,num_max))
                    num = 0
                    point_num -= num_max
                
                res[row_pos,col_pos] = voltage[num]
                num += 1

        # self.ps.receive_packet(4,)
        if not flag:
            self.ps.receive_packet_check(4,"cc550000")

        if out_type == 0:
            return res
        elif out_type == 1:
            return self.voltage_to_cond(voltage=res, read_voltage=read_voltage)
        elif out_type == 2:
            return self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)
    
    def set_reset3(self,row_num_start:int,row_num_end:int,col_num_start:int,col_num_end:int,
                     write_voltage:float,tg:float,pulse_width:float,set_device:bool = True):
        """
            Args:
                row_num_start: 行号左边界
                row_num_end: 行号右边界
                col_num_start: 列号左边界
                col_num_end: 列号右边界

            Returns:
                对应块大小的矩阵
            
                左闭右开
        """
        assert row_num_start>=0 and row_num_start<256 and row_num_end>=0 and row_num_end<=256, "超过界限"
        assert col_num_start>=0 and col_num_start<256 and col_num_end>=0 and col_num_end<=256, "超过界限"

        self.write_voltage = write_voltage
        self.set_op_mode2(read=False,from_row=set_device)
        self.set_pulse_width(pulse_width)
        compiler = self.get_compiler("set_reset.txt")

        const_data,row_data,col_data = self.send_din_ram3(row_num_start,row_num_end,col_num_start,col_num_end,din_ram_start=0)

        for k,v in const_data.items():
            compiler.add_const_variable(k,v)

        ins_data = self.get_dac_ins2(v=write_voltage,tg=tg)
        compiler.add_offset(len(ins_data))
        ins_data = ins_data + compiler.get_ins_data()

        self.execute_ins(ins_data=ins_data,ins_ram_start = 0)

    def set_chip_sel(self,chip_sel = 0):
        """
            选择18个阵列中的一个，chip_sel的范围是0-17
        """
        # assert 0 <= chip_sel <= 17, "芯片编号范围是0-17"

        # if (self.chip_sel) {
        #     print("芯片编号从 {}")
        # }
        self.chip_sel = chip_sel

        # 将chip_sel映射到gpio信号
        map_chipsel_gpio = [0, 1, 4, 5, 16, 17, 20, 21, 64, 65, 68, 69, 80, 81, 84, 85, 256, 257, 260, 261]
        gpio = map_chipsel_gpio[chip_sel]

        # 检查gpio的内容
        # getbits = lambda x, y: (x >> y) & 1
        # print(f"gpio的8/6/4/2/0位: {getbits(gpio, 8)} {getbits(gpio, 6)} {getbits(gpio, 4)} {getbits(gpio, 2)} {getbits(gpio, 0)}")
        # print(f"gpio: {bin(gpio & 0x3FF)}")

        pkts=Packet()
        pkts.append_cmdlist([CMD(EXT_GPIO,command_data=CmdData(gpio)),],mode=1)
        self.ps.send_packets(pkts)

    #------------------------------------------------------------------------------------------
    # *************************************** 模块化执行 ***************************************
    #------------------------------------------------------------------------------------------
    def crossbar_split_to_batch4(self,crossbar:np.ndarray=None,row_index:list[int]=None,col_index:list[int]=None,
                                 from_row:bool = True,split_type:int = 0)->list[list[list[int],list[int]]]:
        """
            Args:
                crossbar: n*n的np矩阵
                row_index: 行号列表
                col_index: 列号列表
                split_type: =0,表示逐行,逐列,这个使用crossbar\n
                            =1,表示逐行,列划分TIA,这个使用crossbar\n
                            =2,表示开所有行,逐列,这个使用crossbar\n

                            =3,表示开所有行,逐列,这个使用row_index和col_index\n
                            =4,表示开所有行,列划分TIA,这个使用row_index和col_index\n
                            =5,表示开所有行,所有列,这个使用row_index和col_index\n

                from_row: True表示按上面的描述进行切分,False表示交换行列的切分方式\n
        """
        if split_type<3:
            row, col = crossbar.shape
            
        operator_batch = []
        if split_type == 0:                 # 逐行,逐列,使用笛卡尔积进行优化
            for di in range(2):
                for dj in range(2):
                    i_indices = range(di, row, 2)
                    j_indices = range(dj, col, 2)
                    operator_batch.extend([[[i], [j]] for i, j in itertools.product(i_indices, j_indices) if crossbar[i][j]])
        elif split_type == 1:               # 逐行,列划分TIA
            if from_row:
                # 从行，就逐行，开所有列，下一步再进行TIA划分
                for di in range(2):
                    for i in range(di,row,2):
                        cols = np.where(crossbar[i,:])[0].tolist()
                        if cols:
                            cols_tia_split = self.setting.tia_split_from_index(index=cols,col=True)
                            # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面
                            operator_batch.extend([[rows,cols] for cols,rows in itertools.product(cols_tia_split,[[i]])])
            else:
                # 从列，就逐列，开所有行，下一步再进行TIA划分
                for dj in range(2):
                    for j in range(dj,col,2):
                        rows = np.where(crossbar[:,j])[0].tolist()
                        if rows:
                            rows_tia_split = self.setting.tia_split_from_index(index=rows,col=False)
                            # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面
                            operator_batch.extend([[rows,cols] for rows,cols in itertools.product(rows_tia_split,[[j]])])
        elif split_type == 2:               # 开所有行,逐列,这个使用crossbar
            if not from_row:
                # 从列，就逐行开所有列
                for di in range(2):
                    for i in range(di,row,2):
                        cols = np.where(crossbar[i,:])[0].tolist()
                        if cols: operator_batch.extend([[[i],cols]])
            else:
                # 从行，就逐列开所有行
                for dj in range(2):
                    for j in range(dj,col,2):
                        rows = np.where(crossbar[:,j])[0].tolist()
                        if rows: operator_batch.extend([[rows,[j]]])
        elif split_type == 3:               # 开所有行,逐列,这个使用row_index和col_index
            if from_row:
                col_index = [i for i in col_index if i%2==0]+[i for i in col_index if i%2==1]
                # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面,不过这里没区别
                operator_batch.extend([[rows,[col]] for col,rows  in itertools.product(col_index, [row_index])])
            else:
                row_index = [i for i in row_index if i%2==0]+[i for i in row_index if i%2==1]
                operator_batch.extend([[[row],cols] for row, cols in itertools.product(row_index, [col_index])])
        elif split_type == 4:               # 开所有行,列分TIA,这个使用row_index和col_index
            if from_row:
                cols_tia_split = self.setting.tia_split_from_index(index=col_index,col=True)
                operator_batch.extend([[rows,cols] for rows, cols in itertools.product([row_index], cols_tia_split)])
            else:
                # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面,不过这里没区别
                rows_tia_split = self.setting.tia_split_from_index(index=row_index,col=False)
                operator_batch.extend([[rows,cols] for cols,rows in itertools.product([col_index], rows_tia_split)])
        elif split_type == 5:               # 开所有行,所有列,这个使用row_index和col_index
            operator_batch.append([row_index,col_index])
        else:
            print("没有对应的切分类型！")

        return operator_batch
    
    def batch_to_din_ram4(self,operator_batch:list[list[list[int],list[int]]],din_ram_start = 0,row_inversion_type = 0,col_inversion_type = 0):
        """
            Args:
                operator_batch: 每个batch需要处理的数据
                din_ram_start: din_ram存数据的起始地址
                inversion_type: 表示index是怎么配置的
                    =0,表示不使用反转,正常映射
                    =1,表示index中01反转
                    =2,表示只反转对应行/列所在TIA之外的所有索引

            Returns:
                din_ram_data: din_ram要发送的指令
                res_row_bank: 一个个点需要配置的行bank和din_ram_data里面的index的映射\n
                res_col_bank: 一个个点需要配置的列bank和din_ram_data里面的index的映射\n
                res_tia_map: 每个点的TIA映射(写模式返回为空)
        """

        # --------------------------------------------------准备din_ram的数据
        din_ram_pos = din_ram_start+2                                                                   # 因为32bit的0在din_ram_data里面, 所以需要+1
        din_ram_data = []                                                                               # 要发送下去的数据, din_ram的开始存0,用于恢复
        res_row_bank = []                                                                               # 等会配行bank指令执行需要的数据, 单层list
        res_col_bank = []                                                                               # 等会配列bank指令执行需要的数据, 单层list
        res_tia_map  = []                                                                               # 每个点对应的TIA映射,需要提前选好从行列读, 单层list
        din_ram_bank_index_map = {}                                                                     # 用于节约din空间

        din_ram_data.append(CMD(PL_DATA,command_data=CmdData(0)))
        din_ram_data.append(CMD(PL_DATA,command_data=CmdData(0xFFFF_FFFF)))
        din_ram_bank_index_map[0] = 0
        din_ram_bank_index_map[0xFFFF_FFFF] = 1
        # --------------------------------------------------增加映射
        def add_map(res_bank:list,indexs:list[int],inversion_type:int=0) -> None:                              # 增加bank和din_ram_data里面的index的映射
            nonlocal din_ram_pos
            bank8,index32 = self.setting.get_bank_index32(indexs)
            # ------------------------------------------------------------------------------------------# ECRAM特定修改
            if inversion_type == 0:
                pass
            if inversion_type == 1:                                                                     # ECRAM的配置取反
                index32 = 0xFFFF_FFFF ^ index32
            elif inversion_type == 2:
                if index32&0xFFFF >0:
                    index32 = index32 | 0xFFFF_0000
                else:
                    index32 = index32 | 0x0000_FFFF
            # ------------------------------------------------------------------------------------------# ECRAM特定修改
            if din_ram_bank_index_map.get(index32,None) is None:
                din_ram_bank_index_map[index32] = din_ram_pos                                           # 如果前面没有用过这个index, 记录下来
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index32)))
                din_ram_pos = din_ram_pos+1
            res_bank.append((bank8,din_ram_bank_index_map[index32]))

        # 一个个batch进行处理
        for rows,cols in operator_batch:
            rows_banks = self.setting.bank_split_from_index(index=rows)
            res_row_bank.append([])
            for rows_bank_index in rows_banks:
                add_map(res_row_bank[-1],rows_bank_index,row_inversion_type)

            cols_banks = self.setting.bank_split_from_index(index=cols)
            res_col_bank.append([])
            for cols_bank_index in cols_banks:
                add_map(res_col_bank[-1],cols_bank_index,col_inversion_type)

            if self.op_mode == "read":
                res_tia_map.append([])
                if self.from_row:
                    res_tia_map[-1].extend([self.setting.TIA_index_map(i,col=True) for i in cols])
                else:
                    res_tia_map[-1].extend([self.setting.TIA_index_map(i,col=False) for i in rows])

        # length = self.setting.check_din_ram(din_ram_data,din_ram_start)
        # din_ram_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(length)))                
        # din_ram_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(din_ram_start)))
        return din_ram_data,res_row_bank,res_col_bank,res_tia_map

    def prepare_latch_ins4(self,crossbar:np.ndarray=None,row_index:list[int]=None,col_index:list[int]=None,din_ram_start:int = 0,
              from_row:bool = True,split_type:int = 0,row_inversion_type:int = 0,col_inversion_type:int = 0):
        """
            Args:
                crossbar: n*n的np矩阵
                row_index: 行号列表
                col_index: 列号列表
                din_ram_start: din_ram存放的起始地址
                split_type: =0,表示逐行,逐列,这个使用crossbar\n
                            =1,表示逐行,列划分TIA,这个使用crossbar\n
                            =2,表示开所有行,逐列,这个使用crossbar\n

                            =3,表示开所有行,逐列,这个使用row_index和col_index\n
                            =4,表示开所有行,列划分TIA,这个使用row_index和col_index\n
                            =5,表示开所有行,所有列,这个使用row_index和col_index\n

                from_row: True从行给信号,False从列给信号

                inversion_type: 表示index是怎么配置的\n
                            =0,表示不使用反转,正常映射\n
                            =1,表示index中01反转\n
                            =2,表示只反转对应行/列所在TIA之外的所有索引\n
            
            Return:
                din_ram_data: 要发送的din_ram指令
                operator_batch: 每个batch中的行/列数据
                res_tia_map

            为读写准备要配置的指令
        """
        row_banks_last,col_banks_last = None,None
        row_bank_num_last,col_bank_num_last = None,None


        operator_batch = self.crossbar_split_to_batch4(crossbar,row_index,col_index,from_row,split_type)
        din_ram_data,res_row_bank,res_col_bank,res_tia_map = self.batch_to_din_ram4(operator_batch,din_ram_start,row_inversion_type,col_inversion_type)

        ins_data = []

        for row_banks,col_banks in zip(res_row_bank,res_col_bank):
            add_ins_data = []
            row_bank_num_new,col_bank_num_new = [row_bank[0] for row_bank in row_banks],[col_bank[0] for col_bank in col_banks]

            row_flag,col_flag = False,False
            # 行bank号不等,需要先将行bank清零,再配置bank
            if row_bank_num_new!=row_bank_num_last:
                # 清零类型和row_inversion_type有关
                if row_inversion_type>0:
                    add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|1)))
                else:
                    add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(0xFF<<8|0)))
                row_flag = True

            # bank号和index号不等
            if row_flag or row_banks_last!=row_banks:
                for row_bank in row_banks:
                    add_ins_data.append(CMD(PL_ROW_BANK,command_data=CmdData(row_bank[0]<<8|row_bank[1])))  # 配置行bank


            # 列bank号不等,需要先将列bank清零,再配置bank
            if col_bank_num_new!=col_bank_num_last:
                # 清零类型和row_inversion_type有关
                if col_inversion_type>0:
                    add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(0xFF<<8|1)))
                else:
                    add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(0xFF<<8|0)))
                col_flag = True

            # bank号和index号不等
            if col_flag or col_banks_last!=col_banks:
                for col_bank in col_banks:
                    add_ins_data.append(CMD(PL_COL_BANK,command_data=CmdData(col_bank[0]<<8|col_bank[1])))  # 配置列bank


            # 因为把row_ctrl和col_ctrl和sw分离了,所以PL_READ_ROW_PULSE和PL_READ_COL_PULSE,一样的效果
            # add_ins_data.append(CMD(PL_READ_ROW_PULSE,command_data=CmdData(dout_ram_pos)))

            row_banks_last,col_banks_last = row_banks,col_banks
            row_bank_num_last,col_bank_num_last = row_bank_num_new,col_bank_num_new
            
            # 读写指令在外部进行处理，比如多重读
            ins_data.append(add_ins_data)

        return ins_data,din_ram_data,operator_batch,res_tia_map

    def read4(self,crossbar:Union[np.ndarray,None]=None,row_index:Union[list[int],None]=None,col_index:Union[list[int],None]=None,
              read_voltage:float=0.1,tg:float = 5,gain:int = 1,sub_base:bool = False,
              from_row:bool = True,split_type:int = 0,row_type:int = 0,col_type:int = 0):
        """
            Args:
                crossbar: n*n的np矩阵
                row_index: 行号列表
                col_index: 列号列表
                sub_base: 表示减去0v读的电压

                split_type: =0,表示逐行,逐列,这个使用crossbar\n
                            =1,表示逐行,列划分TIA,这个使用crossbar\n
                            =2,表示开所有行,逐列,这个使用crossbar\n

                            =3,表示开所有行,逐列,这个使用row_index和col_index\n
                            =4,表示开所有行,列划分TIA,这个使用row_index和col_index\n
                            =5,表示开所有行,所有列,这个使用row_index和col_index\n

                from_row: True从行给信号,False从列给信号

                row_type/col_type: 表示index是怎么配置的\n
                            =0,表示不使用反转,正常映射\n
                            =1,表示index中01反转\n
                            =2,表示只反转对应行/列所在TIA之外的所有索引\n
            
            Return:
                如果是逐点,则返回一个256*256的矩阵,求和则返回一个一维的256个元素的np数组
            返回读出来的电压(V),电导(uS),电阻(kΩ)
        """
        assert (crossbar is not None and split_type<=2) or (row_index is not None and col_index is not None and split_type>2),"read4: split_type接收数据错误!"
        self.read_voltage = read_voltage
        self.set_tia_gain(gain)
        self.set_op_mode2(read=True,from_row=from_row)

        din_ram_start,ins_ram_start = 0,0
        dout_ram_start,dout_ram_pos = 0,0
        read_ins = PL_READ_ROW_PULSE if from_row else PL_READ_COL_PULSE
        pre_ins_data,din_ram_data,operator_batch,res_tia_map = self.prepare_latch_ins4(crossbar,row_index,col_index,din_ram_start,from_row,split_type,row_type,col_type)

        # 发送din_ram的数据
        # self.send_cmd(cmd=din_ram_data,mode=5)
        # din_ram_data.clear()
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)

        # 返回的数据
        if split_type<2:
            res = np.zeros((self.setting.chip_latch_num,self.setting.chip_latch_num))
        elif from_row:
            res = np.zeros((self.setting.chip_latch_num))
        else:
            res = np.zeros((self.setting.chip_latch_num))

        def get_read_result(rows,cols,tias,curr,read_batch_start,res,voltage,sub_base):
            # 大于等于2表示，开所有行/列
            if split_type>=2:
                if from_row:
                    for col,tia in zip(cols,tias):
                        res[col] = voltage[curr-read_batch_start,tia]-voltage[curr+1-read_batch_start,tia] if sub_base else voltage[curr-read_batch_start,tia]
                else:
                    for row,tia in zip(rows,tias):
                        res[row] = voltage[curr-read_batch_start,tia]-voltage[curr+1-read_batch_start,tia] if sub_base else voltage[curr-read_batch_start,tia]
            else:
                if from_row:
                    for col,tia in zip(cols,tias):
                        # print(col,tia,voltage[curr-read_batch_start,tia],voltage[curr+1-read_batch_start,tia])
                        res[rows[0],col]=voltage[curr-read_batch_start,tia]-voltage[curr+1-read_batch_start,tia] if sub_base else voltage[curr-read_batch_start,tia]
                else:
                    for row,tia in zip(rows,tias):
                        res[row,cols[0]] = voltage[curr-read_batch_start,tia]-voltage[curr+1-read_batch_start,tia] if sub_base else voltage[curr-read_batch_start,tia]

        ins_data = self.get_dac_ins2(v=read_voltage,tg=tg)
        read_batch_start,read_batch_end = 0,0
        interval = 2 if sub_base else 1
        # 遍历每个batch
        for ins in pre_ins_data:
            if sub_base:
                ins.extend(self.get_dac_ins2(v=read_voltage))
            # 因为把row_ctrl和col_ctrl和sw分离了,所以PL_READ_ROW_PULSE和PL_READ_COL_PULSE,一样的效果
            ins.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))
            # 如果要减去base的话，就配置电压为0，再读一次就好
            pos = len(ins)
            if sub_base:
                ins.extend(self.get_dac_ins2(v=0))
                ins.append(CMD(read_ins,command_data=CmdData(dout_ram_pos+1)))
            # 因为后面会加一个exit指令
            if len(ins_data)+len(ins)+1 >= self.setting.ins_ram_length or dout_ram_pos+2 > self.setting.dout_ram_length:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
                voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
                for i in range(read_batch_start,read_batch_end):
                    rows,cols = operator_batch[i]
                    tias = res_tia_map[i]
                    get_read_result(rows,cols,tias,i*interval,read_batch_start*interval,res,voltage,sub_base)
                
                read_batch_start = read_batch_end
                dout_ram_pos = dout_ram_start
                # 读两次
                if sub_base:
                    ins[pos-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))
                    ins[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos+1))
                else:
                    ins[-1]=CMD(read_ins,command_data=CmdData(dout_ram_pos))

            ins_data.extend(ins)
            dout_ram_pos += interval
            read_batch_end += 1

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            voltage = self.adc.get_out2(data_length=dout_ram_pos-dout_ram_start,dout_ram_start=dout_ram_start)
            for i in range(read_batch_start,read_batch_end):
                rows,cols = operator_batch[i]
                tias = res_tia_map[i]
                get_read_result(rows,cols,tias,i*interval,read_batch_start*interval,res,voltage,sub_base)

        # 返回电压电导电阻
        return res,self.voltage_to_cond(voltage=res, read_voltage=read_voltage),self.voltage_to_resistance(voltage=res, read_voltage=read_voltage)
    
    def write4(self,crossbar:np.ndarray=None,row_index:list[int]=None,col_index:list[int]=None,
              write_voltage:float=1,tg:Union[float|np.ndarray]= 5,pulse_width:float = 1e-6,
              set_device:bool = True,split_type:int = 0,row_type:int = 0,col_type:int = 0):
        """
            Args:
                crossbar: n*n的np矩阵
                row_index: 行号列表
                col_index: 列号列表
                sub_base: 表示减去0v读的电压

                split_type: =0,表示逐行,逐列,这个使用crossbar\n
                            =1,表示逐行,列划分TIA,这个使用crossbar\n
                            =2,表示开所有行,逐列,这个使用crossbar\n

                            =3,表示开所有行,逐列,这个使用row_index和col_index\n
                            =4,表示开所有行,列划分TIA,这个使用row_index和col_index\n
                            =5,表示开所有行,所有列,这个使用row_index和col_index\n

                set_device: True从行给信号,按split_type,False从列给信号,split_type中的行列互换

                inversion_type: 表示index是怎么配置的\n
                            =0,表示不使用反转,正常映射\n
                            =1,表示index中01反转\n
                            =2,表示只反转对应行/列所在TIA之外的所有索引\n
        """
        assert (crossbar is not None and split_type<=2) or (row_index is not None and col_index is not None and split_type>2),"write4: split_type接收数据错误!"
        self.write_voltage = write_voltage
        self.set_op_mode2(read=False,from_row=set_device)
        self.set_pulse_width(pulse_width)

        din_ram_start,ins_ram_start = 0,0
        write_ins = PL_WRITE_ROW_PULSE if set_device else PL_WRITE_COL_PULSE
        pre_ins_data,din_ram_data,operator_batch,res_tia_map = self.prepare_latch_ins4(crossbar,row_index,col_index,din_ram_start,set_device,split_type,row_type,col_type)

        # 发送din_ram的数据
        # self.send_cmd(cmd=din_ram_data,mode=5)
        # din_ram_data.clear()
        self.execute_send_din_data(din_ram_data=din_ram_data,din_ram_start=din_ram_start)

        change_tg,tg_last = type(tg)==np.ndarray,-1
        ins_data = self.get_dac_ins2(v=write_voltage,tg=None) if change_tg else self.get_dac_ins2(v=write_voltage,tg=tg)
        # 遍历每个batch
        for i,ins in enumerate(pre_ins_data):
            # 改变tg的电压
            if change_tg:
                tg_v = tg[operator_batch[i][0][0],operator_batch[i][1][0]]
                if tg_v!=tg_last:
                    tmp_ins_data +=self.get_dac_ins2(tg=tg_v)
                    tg_last = tg_v

            ins.append(CMD(write_ins))
            if len(ins_data)+len(ins)+1 >= self.setting.ins_ram_length:
                self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)
            ins_data.extend(ins)

        if len(ins_data)>0:
            self.execute_ins(ins_data=ins_data,ins_ram_start=ins_ram_start)


    def send_ps_ddr5(self,ddr_data,mode,ps_ddr_pos):
        """
            给ddr发指令,ps_ddr_pos按4B进行寻址,但是下面的DDR传数据需要32B为单位
        """
        ins_num = len(ddr_data)
        ddr_one = 8
        if mode==8 or mode==9:
            # 常规指令模式,开头一个32B的，
            ddr_data.insert(0,CMD(PS_DATA_LENGTH,command_data=CmdData(ins_num)))
            ddr_data.insert(0,CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos)))
            ps_ddr_pos += ddr_one + int(np.ceil(ins_num/ddr_one))*ddr_one
        elif mode==10:
            # register指令
            ddr_data.insert(0,CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos)))
            ps_ddr_pos += ddr_one
        elif mode==11:
            # 不管是finsh,还是start,finsh占用4B,start不占用空间,这里懒的写判断了，直接都占用
            ddr_data.insert(0,CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos)))
            ps_ddr_pos += ddr_one
        else:
            print("发送ps的DDR数据出错")
        pkts=Packet()
        pkts.append_single(ddr_data,mode=mode)
        self.ps.send_packets(pkts,message_check=None)
        ddr_data.clear()
        return ps_ddr_pos

    def set_op_mode5(self,ps_ddr_pos,read=True,from_row=True,return_ins=False):
        """
            Args:
                read: True配置为读模式, False配置为写模式
                from_row: True配置为从行读/写, False配置为从列读/写

            Functions:
                如果模式和上次不一样,会将所有的DAC通道电压设置为0
        """
        ins_data=[]
        if (read and self.op_mode != "read") or (not read and self.op_mode == "read"):
            ins_data.extend([CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16)) for i in range(12)])
        self.from_row = from_row
        self.op_mode = "read" if read else "write"
            
        if self.setting.deviceType == 1:
            ps_ddr_pos = self.send_ps_ddr5(ddr_data=[CMD(SER_DATA,command_data=CmdData(self.op_mode != "read"))],mode=10,ps_ddr_pos=ps_ddr_pos)
            if self.op_mode == "write":
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(1<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
            else:
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(int(from_row)<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
        else:
            if self.setting.IsRERAM512:
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))
            else:
                ins_data.append(CMD(PL_ROW_CTRLI,command_data=CmdData(int(from_row)<<16)))                                                  # 1配置行到施加电压,
                ins_data.append(CMD(PL_COL_CTRLI,command_data=CmdData(int(not from_row)<<16)))                                                  # 0配置列到TIA,
                ins_data.append(CMD(PL_ROW_COL_SWI,command_data=CmdData(int(from_row)<<16)))  
        ps_ddr_pos = self.send_ps_ddr5(ddr_data=ins_data,mode=9,ps_ddr_pos=ps_ddr_pos)
        return ps_ddr_pos


    def write5(self,crossbar:np.ndarray=None,row_index:list[int]=None,col_index:list[int]=None,
              write_voltage:float=1,tg:float = 5,pulse_width:float = 1e-6,
              set_device:bool = True,split_type:int = 0,row_type:int = 0,col_type:int = 0,
              ps_ddr_pos=0):
        """
            Args:
                crossbar: n*n的np矩阵
                row_index: 行号列表
                col_index: 列号列表
                sub_base: 表示减去0v读的电压

                split_type: =0,表示逐行,逐列,这个使用crossbar\n
                            =1,表示逐行,列划分TIA,这个使用crossbar\n
                            =2,表示开所有行,逐列,这个使用crossbar\n

                            =3,表示开所有行,逐列,这个使用row_index和col_index\n
                            =4,表示开所有行,列划分TIA,这个使用row_index和col_index\n
                            =5,表示开所有行,所有列,这个使用row_index和col_index\n

                set_device: True从行给信号,按split_type,False从列给信号,split_type中的行列互换

                inversion_type: 表示index是怎么配置的\n
                            =0,表示不使用反转,正常映射\n
                            =1,表示index中01反转\n
                            =2,表示只反转对应行/列所在TIA之外的所有索引\n
        """
        assert (crossbar is not None and split_type<=2) or (row_index is not None and col_index is not None and split_type>2),"write4: split_type接收数据错误!"
        self.write_voltage = write_voltage
        ps_ddr_pos = self.set_op_mode5(ps_ddr_pos=ps_ddr_pos,read=False,from_row=set_device)
        ps_ddr_pos = self.send_ps_ddr5(ddr_data=self.clk_manager.set_pulse_cyc_ins(pulsewidth=pulse_width),mode=10,ps_ddr_pos=ps_ddr_pos)

        
        write_ins = PL_WRITE_ROW_PULSE if set_device else PL_WRITE_COL_PULSE
        pre_ins_data,din_ram_data,operator_batch,res_tia_map = self.prepare_latch_ins4(crossbar,row_index,col_index,0,set_device,split_type,row_type,col_type)

        # 发送din_ram的数据
        ps_ddr_pos = self.send_ps_ddr5(din_ram_data,mode=8,ps_ddr_pos=ps_ddr_pos)
        change_tg,tg_last = type(tg)==np.ndarray,-1
        ins_data = self.get_dac_ins2(v=write_voltage,tg=None) if change_tg else self.get_dac_ins2(v=write_voltage,tg=tg)

        # 遍历每个batch
        for i,ins in enumerate(pre_ins_data):
            # 改变tg的电压
            if change_tg:
                tg_v = tg[operator_batch[i][0][0],operator_batch[i][1][0]]
                if tg_v!=tg_last:
                    tmp_ins_data +=self.get_dac_ins2(tg=tg_v)
                    tg_last = tg_v
            # 准备读指令
            ins.append(CMD(write_ins))
            if len(ins_data)+len(ins)+1 >= self.setting.ins_ram_length:
                ins_data.append(CMD(PL_EXIT))
                ps_ddr_pos = self.send_ps_ddr5(ins_data,mode=9,ps_ddr_pos=ps_ddr_pos)
            ins_data.extend(ins)

        if len(ins_data)>0:
            ins_data.append(CMD(PL_EXIT))
            ps_ddr_pos = self.send_ps_ddr5(ins_data,mode=9,ps_ddr_pos=ps_ddr_pos)
        return ps_ddr_pos