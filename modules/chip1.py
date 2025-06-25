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
import os

from typing import List, Union

class CHIP1():
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

    #------------------------------------------------------------------------------------------
    # ************************************** 读相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def set_tia_gain(self,gain:int):
        """
            Args:
                设置TIA的增益为gain
        """
        self.adc.set_gain(gain)
    
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
                            =6,表示逐行逐列,这个使用row_index和col_index\n
                            =7,表示逐行,列划分TIA,这个使用row_index和col_index\n

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
        elif split_type == 6:
            row_index = [i for i in row_index if i%2==0]+[i for i in row_index if i%2==1]
            col_index = [i for i in col_index if i%2==0]+[i for i in col_index if i%2==1]
            operator_batch.extend([[[i], [j]] for i, j in itertools.product(row_index, col_index) if crossbar[i][j]])
        elif split_type == 7:               # 逐行,列划分TIA
            if from_row:
                row_index = [i for i in row_index if i%2==0]+[i for i in row_index if i%2==1]
                cols_tia_split = self.setting.tia_split_from_index(index=col_index,col=True)
                # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面
                operator_batch.extend([[[row],cols] for cols,row in itertools.product(cols_tia_split,row_index)])
            else:
                col_index = [i for i in col_index if i%2==0]+[i for i in col_index if i%2==1]
                rows_tia_split = self.setting.tia_split_from_index(index=row_index,col=False)
                # 这里优化一下，尽量先遍历配置bank少的, bank配置多的放在前面
                operator_batch.extend([[rows,[col]] for rows,col in itertools.product(rows_tia_split,col_index)])
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
                            =6,表示逐行逐列,这个使用row_index和col_index\n
                            =7,表示逐行,列划分TIA,这个使用row_index和col_index\n

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
                            =6,表示逐行逐列,这个使用row_index和col_index\n
                            =7,表示逐行,列划分TIA,这个使用row_index和col_index\n

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
        if split_type<2 or split_type>5:
            res = np.zeros((self.setting.chip_latch_num,self.setting.chip_latch_num))
        elif from_row:
            res = np.zeros((self.setting.chip_latch_num))
        else:
            res = np.zeros((self.setting.chip_latch_num))

        def get_read_result(rows,cols,tias,curr,read_batch_start,res,voltage,sub_base):
            # 大于等于2表示，开所有行/列
            if split_type>=2 and split_type<=5:
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
                            =6,表示逐行逐列,这个使用row_index和col_index\n
                            =7,表示逐行,列划分TIA,这个使用row_index和col_index\n

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

        time_out = pulse_width*(len(operator_batch)+1) + 1
        self.ps.set_time_out(time_out=time_out)
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
        self.ps.set_time_out(time_out=1)

        if flag == 0:
            # 先finsh
            ins_data = [CMD(PS_START_FINSH,command_data=CmdData(1)),CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos_start))]
            ps_ddr_pos=self.send_ps_ddr5(ddr_data=ins_data,mode=11,ps_ddr_pos=ps_ddr_pos)
        elif flag == 1:
            # 再start
            ins_data = [CMD(PS_START_FINSH,command_data=CmdData(0)),CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos_start))]
            ps_ddr_pos=self.send_ps_ddr5(ddr_data=ins_data,mode=11,ps_ddr_pos=ps_ddr_pos)
            ps_ddr_pos = ps_ddr_pos-1
        elif flag == 2:
            # 先finsh
            ins_data = [CMD(PS_START_FINSH,command_data=CmdData(1)),CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos_start))]
            ps_ddr_pos=self.send_ps_ddr5(ddr_data=ins_data,mode=11,ps_ddr_pos=ps_ddr_pos)
            # 再start
            ins_data = [CMD(PS_START_FINSH,command_data=CmdData(0)),CMD(PS_DDR_ADDR,command_data=CmdData(ps_ddr_pos_start))]
            ps_ddr_pos=self.send_ps_ddr5(ddr_data=ins_data,mode=11,ps_ddr_pos=ps_ddr_pos)
            ps_ddr_pos = ps_ddr_pos-1
        return ps_ddr_pos