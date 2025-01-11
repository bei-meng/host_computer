from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS
from modules.adc import ADC
from modules.dac import DAC
import numpy as np

class CHIP():
    """
        对chip进行的操作
    """
    deviceType = 0                  # 器件类型0: RERAM,1: ECRAM
    latch_cyc = 2                   # PCB上锁存器的latch cycle树
    reg_clk_cyc = 2                 # 高电平cycle数，1 cycle=10ns 0：翻转
    latch_clk_cyc = 2               # 高电平cycle数，1 cycle=10ns 0：翻转
    pulse_cyc = 256                 # row/col pulse的cycle数 0：翻转"


    pulse_cyc_length = 10*1e-9      # 每个cycle的宽度为10ns

    read_from_row = True            # 从行读的模式
    read_voltage = None             # 读电压

    write_from_row = True           # 从行写的模式
    write_voltage = None            # 写电压

    op_mode = None                  # 当前所处模式


    ps = None
    adc = None
    dac = None

    def __init__(self, ps:PS):
        self.ps = ps
        self.initOp()
        self.adc = ADC(ps)
        self.dac = DAC(ps)

    def get_setting_info(self):
        """
            输出相关信息
        """
        device = "ECRAM" if self.deviceType else "ReRAM"
        if self.op_mode == "read":
            row_col_read = "行" if self.read_from_row else "列"
            res = f"操作模式：{self.op_mode}\t器件：{device}\t读电压：{self.read_voltage}v\t从行\列给电压：{row_col_read}\tTIA增益：{self.adc.gain}"
        elif self.op_mode == "write":
            row_col_write = "行" if self.write_from_row else "列"
            res = f"操作模式：{self.op_mode}\t器件：{device}\t写电压：{self.write_voltage}v\t从行\列给电压：{row_col_write}\t脉宽：{self.pulse_cyc}"
        else:
            res = f"未配置操作模式。"
        return res

    #------------------------------------------------------------------------------------------
    # ********************************** 器件初始化及相关配置 ***********************************
    #------------------------------------------------------------------------------------------
    def initOp(self):
        """
            chip的初始化操作
        """
        # 配置器件的初始化
        self.set_device_cfg(deviceType=0,reg_clk_cyc=0xF,latch_clk_cyc=0xF)
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(FLT,command_data=CmdData(0x0FFF)),                  # 配置flt
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le1)),         # cfg_flt_le1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le2)),         # cfg_flt_le2
            CMD(CIM_RESET,command_data=CmdData(1)),                 # reset指令
            CMD(CIM_SS,command_data=CmdData(1)),                    # reg写入数据打开
            CMD(SER_PARA_SEL,command_data=CmdData(1)),              # 切换到并行模式
            # CMD(NEGTIVE_REG_CLK,command_data=CmdData(1)),                                       # negtive_reg_clk
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

        # 不为空就执行初始化
        if self.adc is not None:
            self.adc.initOp()
        if self.dac is not None:
            self.dac.initOp()

    def set_device_cfg(self,deviceType = None,latch_cyc = None, reg_clk_cyc= None, latch_clk_cyc = None):
        """
            设置device的cfg
        """
        self.deviceType = self.deviceType if deviceType is None else deviceType
        self.latch_cyc = self.latch_cyc if latch_cyc is None else latch_cyc
        self.reg_clk_cyc = self.reg_clk_cyc if reg_clk_cyc is None else reg_clk_cyc
        self.latch_clk_cyc = self.latch_clk_cyc if latch_clk_cyc is None else latch_clk_cyc

        data = self.deviceType | self.latch_cyc<<1 | self. reg_clk_cyc<<3 | self.latch_clk_cyc<<7
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(DEVICE_CFG,command_data=CmdData(data)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

    def set_pulse_width(self,pulsewidth):
        """
            设置施加的脉宽的宽度
        """
        pulse_cyc=int(pulsewidth/self.pulse_cyc_length)
        assert pulse_cyc>=0 ,"set_pulse_width: 脉宽超过界限！"

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(PULSE_CYC,command_data=CmdData(pulse_cyc)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

        self.pulse_cyc = pulse_cyc
    
    #------------------------------------------------------------------------------------------
    # ********************************* 配置latch，行列的映射 **********************************
    #------------------------------------------------------------------------------------------
    def numToBank_Index(self,num:int):
        """
            注意：num从0索引开始
            将x,y译码为对应的bank和index
            bank和index均从0开始，方便后面的位操作
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
    
    def get_data(self,num:list):
        """
            返回已经切分好的行或列，对应的bank，index
        """
        bank,index = 0,0
        for i in num:
            bank_tmp,index_tmp = self.numToBank_Index(i)
            bank = bank | (1<<bank_tmp)
            index = index | (1<<index_tmp)
        return bank,index

    def get_bank_tia(self,num:list):
        """
            对应行号列号，映射为bank，index，tia
        """
        res = []
        for k,v in enumerate(num):
            bank,index = self.numToBank_Index(v)
            if self.op_mode=="read":
                tia = self.adc.TIA_index_map(v,device=self.deviceType,col=self.read_from_row)
            elif self.op_mode=="write":
                tia = self.adc.TIA_index_map(v,device=self.deviceType,col=self.write_from_row)
            else:
                print("get_bank_tia：未设置模式。")
            res.append((k,v,bank,index,tia))
        return res
            
    def set_cim_reset(self):
        """
            发送reset的指令
        """
        pkts=Packet()
        # reset指令
        pkts.append_cmdlist([
            CMD(CIM_RESET,command_data=CmdData(0)),
            CMD(CIM_RESET,command_data=CmdData(1)),
        ],mode=1)
        self.ps.send_packets(pkts)

    def temp_negative_reg_clk(self,data):
        """
            设置NEGTIVE_REG_CLK=data
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(NEGTIVE_REG_CLK,command_data=CmdData(self.data)),
        ],mode=1)   
        self.ps.send_packets(pkts)

    def set_latch(self,num:list[list],row=True,value=None):
        """
            将对应的行或列配置成latch为1,
            num: 为嵌套列表,第一层表示有几个bank,第二层表示bank中需要修改的行号和列号,从0开始
        """
        row_col_sel = 1 if row else 0
        pkts=Packet()
        # 配置行
        for i in num:
            if len(i)>0:
                bank,index = self.get_data(i)
                # 如果是要将32bit的值改成对应的值
                if value is not None:
                    index = value
                pkts.append_cmdlist([
                    # 行reg配置
                    CMD(CIM_DATA_IN,command_data=CmdData(index)),                                       # 第index位置1
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk
                    # CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.negative_reg_clk)),     # negative_reg_clk
                    # CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_pos_reg_clk)),      # negative_reg_clk

                    # 行bank配置
                    CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
                    CMD(CIM_BANK_SEL,command_data=CmdData(bank)),                                       # 行bank选择
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
                    CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
                ],mode=1)   
        self.ps.send_packets(pkts)

    def set_bank_latch(self,banknum:list,row=True,value=0):
        """
            将对应行/列的bank配置成对应的值
            banknum: 为要修改的bank的列表, 从0开始
            row: 表示是修改的row的,还是col的
            value: 为对应要修改32bit的值
        """
        assert len(banknum)>0,"set_bank_latch：空列表。"
        row_col_sel = 1 if row else 0

        tmp = 0
        pkts=Packet()
        # 配置行
        for i in banknum:
            tmp = tmp | (1<<i)
        pkts.append_cmdlist([
            # 行reg配置
            CMD(CIM_DATA_IN,command_data=CmdData(value)),                                       # 第xindex位置1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk
            # CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.negative_reg_clk)),     # negative_reg_clk
            # CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_pos_reg_clk)),      # negative_reg_clk

            # 行bank配置
            CMD(ROW_COL_SEL,command_data=CmdData(row_col_sel)),                                 # 设置为行/列模式
            CMD(CIM_BANK_SEL,command_data=CmdData(tmp)),                                        # bank选择
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
        ],mode=1)   
        self.ps.send_packets(pkts)

    def clear_dac_v(self):
        """
            清空dac
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
    #------------------------------------------------------------------------------------------
    # ************************************** 读相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def set_read_mode(self,row=True,delay=None):
        """
            设置read的模式,从行读的配置,从列读的配置
        """
        self.clear_dac_v()
        self.op_mode = "read"
        self.read_from_row = row
        if self.read_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(1)),                                                  # 配置行到施加电压
                CMD(COL_CTRL,command_data=CmdData(0)),                                                  # 配置列到TIA
                CMD(ROW_COL_SW,command_data=CmdData(1)),                                                # PCB上的TIA接在列
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(0)),                                                  # 配置行到TIA
                CMD(COL_CTRL,command_data=CmdData(1)),                                                  # 配置列到电压
                CMD(ROW_COL_SW,command_data=CmdData(0)),                                                # PCB上的TIA接在行
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)

    def set_dac_read_V(self,v:float,tg_v:float = 5):
        """
            配置dac的读电压
        """
        self.read_voltage = v
        if self.deviceType==0:
            if self.read_from_row:
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             #

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             #
                self.dac.set_voltage(tg_v,dac_num=0,dac_channel=6)          # TG
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             #  
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             #
            else:   
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             #

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             #
                self.dac.set_voltage(tg_v,dac_num=0,dac_channel=6)             # TG
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             #    
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             #
        elif self.deviceType==1:    
            if self.read_from_row:  
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)             # ROW_Va电压

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=6)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             # COL_Va电压

                # self.dac.set_voltage(0,dac_num=1,dac_channel=0)             # ROW_Vc
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             # COL_Vc     
                # self.dac.set_voltage(0,dac_num=1,dac_channel=2)             # GL
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             # GR
            else:   
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             # ROW_Va电压

                self.dac.set_voltage(v,dac_num=0,dac_channel=4)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)             # COL_Va电压

                # self.dac.set_voltage(0,dac_num=1,dac_channel=0)             # ROW_Vc
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             # COL_Vc     
                # self.dac.set_voltage(0,dac_num=1,dac_channel=2)             # GL
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             # GR

    def set_tia_gain(self,gain:int):
        """
            设置TIA的增益
        """
        self.adc.set_gain(gain)

    def generate_read_pulse(self):
        """
            产生读脉冲的指令
        """
        if self.read_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                             # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),         # cfg_col_pulse，配置列为常1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_read)),          # 然后开始读,行给电压
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),         # cfg_col_pulse，读完后，把列电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                             # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),         # cfg_row_pulse，配置行为常1
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_read)),          # 然后开始读,列给电压
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),         # cfg_row_pulse，读完后，把行电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)

    def get_tia_out(self,num:list):
        """
           得到tia的输出 
        """
        assert self.op_mode == "read","未设置为读模式。"
        assert self.read_voltage is not None,"未设置读电压。"
        cond,voltage = self.adc.get_out(num,self.read_voltage)
        
        return np.array(cond),np.array(voltage)
    
    def set_read(self, row:bool, v:float, gain:int, tg_v:float = 5):
        """
            封装
        """
        self.set_read_mode(row=row)
        self.set_dac_read_V(v,tg_v=tg_v)
        self.set_tia_gain(gain=gain)
    
    def read_one(self,row_index:int,col_index:int):
        """
            读某一个器件，row_index为行索引，col_index为列索引
        """
        print(self.get_setting_info())
        assert self.op_mode == "read","未设置为读模式。"
        assert self.read_voltage is not None,"未设置读电压。"

        if not self.read_from_row:
            row_index, col_index = col_index, row_index
        self.set_cim_reset()                                                                        # 先reset 
        self.set_latch([[row_index]],row=self.read_from_row,value=None)                             # 配置行
        self.set_latch([[col_index]],row=not self.read_from_row,value=None)                         # 配置列
        self.generate_read_pulse()                                                                  # 产生读脉冲
        
        tia_index = self.adc.TIA_index_map(col_index,self.deviceType,self.read_from_row)
        cond,voltage = self.adc.get_out([tia_index],read_voltage=self.read_voltage)
        
        return cond,voltage

    def read(self,row_index:list,col_index:list,debug = False):
        """
            读器件，row_index为行索引，col_index为列索引
        """
        print(self.get_setting_info())
        assert self.op_mode == "read","未设置为读模式。"
        assert self.read_voltage is not None,"未设置读电压。"

        if not self.read_from_row:
            row_index, col_index = col_index, row_index

        # ----------------------------------------------行数据映射
        index_data_row = self.get_bank_tia(row_index)
        bank8_row = [[] for _ in range(8)]
        for j in index_data_row:
            bank8_row[j[2]].append(j[1])
        if debug:
            print("映射输入端的bank:",bank8_row)
        # ----------------------------------------------列数据映射
        index_data = self.get_bank_tia(col_index)                                                 # 映射得到i,num,bank，index，tia
        # print(index_data)
        # ----------------------------------------------映射16路tia
        tia16 = [[] for _ in range(16)]
        for i in index_data:
            # print(i)
            tia16[i[4]].append(i)
        # print("tia16",tia16)
        # ----------------------------------------------每路TIA选一路
        flag = True
        read_num = []
        while flag:
            flag = False
            tmp = []
            for i in tia16:
                if len(i)>0:
                    tmp.append(i.pop())                 # 每路tia选一个值
                    flag = True
            if flag == True:
                read_num.append(tmp)
        # print("选择16路tia")
        # for i in read_num:
        #     print(i)
        # ----------------------------------------------循环去读
        read_res_cond = []
        read_res_voltage = []
        for i in read_num:
            # ------------------------------------------reset然后配置行
            self.set_cim_reset()                                                                      # 先reset 
            self.set_latch(bank8_row,row=self.read_from_row,value=None)                             # 配置行
            # ------------------------------------------映射8个bank
            bank8 = [[] for _ in range(8)]
            for j in i:
                bank8[j[2]].append(j[1])
            if debug:
                print("映射读出端的bank:",bank8)
                print("映射读出端的TIA:",[j[4] for j in i])
            # ------------------------------------------开始配置列latch,如果从行读，row=False，从列读，row=True
            self.set_latch(bank8,row=not self.read_from_row,value=None)
            # ------------------------------------------给读脉冲
            self.generate_read_pulse() 
            # ------------------------------------------读出结果
            cond,voltage = self.adc.get_out([j[4] for j in i],read_voltage=self.read_voltage)
            read_res_cond.append(cond)
            read_res_voltage.append(voltage)
        # ----------------------------------------------将结果映射回原来的顺序
        result_cond = [0]*len(col_index)
        result_v = [0]*len(col_index)
        for i,v1 in enumerate(read_num):
            for j,v2 in enumerate(v1):
                result_cond[v2[0]]=read_res_cond[i][j]
                result_v[v2[0]]=read_res_voltage[i][j]
        return np.array(result_cond),np.array(result_v)

    def read_all(self,row_index: list, col_index: list,
                 row_value  = None, col_value = None,
                 all_tia = True, debug = False):
        """
            不检查TIA映射的问题
        """
        print(self.get_setting_info())
        assert self.op_mode == "read","未设置为读模式。"
        assert self.read_voltage is not None,"未设置读电压。"
        if not self.read_from_row:
            row_index, col_index = col_index, row_index
            row_value, col_value = col_value, row_value
        # ----------------------------------------------行列数据映射
        row_data = self.get_bank_tia(row_index)
        row_bank = [[] for _ in range(8)]
        row_bank_list = []
        for j in row_data:
            row_bank[j[2]].append(j[1])
            row_bank_list.append(j[2])

        col_data = self.get_bank_tia(col_index)
        col_bank = [[] for _ in range(8)]
        col_bank_list = []
        for j in col_data:
            col_bank[j[2]].append(j[1])
            col_bank_list.append(j[2])
        # ----------------------------------------------配置行列bank,因为bank配同样的值能加速
        self.set_cim_reset()
        if row_value is not None:
            self.set_bank_latch(row_bank_list,row=self.read_from_row,value=row_value)
        else:
            self.set_latch(row_data,row=self.read_from_row,value=row_value)
        if col_value is not None:
            self.set_bank_latch(col_bank_list,row=not self.read_from_row,value=col_value)
        else:
            self.set_latch(col_data,row=not self.read_from_row,value=col_value)
        if debug:
            # (k,v,bank,index,tia)
            print("映射输入端的bank:",row_bank)
            print("映射输出端的bank:",col_bank)
            print("映射读出端的TIA:",[j[4] for j in col_bank])
        # ----------------------------------------------读操作
        self.generate_read_pulse()
        if all_tia:
            cond,voltage = self.adc.get_out([i for i in range(16)],read_voltage=self.read_voltage)
        else:
            cond,voltage = self.adc.get_out([j[4] for j in col_data],read_voltage=self.read_voltage)
        return cond,voltage

    #------------------------------------------------------------------------------------------
    # ************************************** 写相关操作 ****************************************
    #------------------------------------------------------------------------------------------
    def set_write_mode(self,row=True,delay=None):
        """
            设置write的模式,从行写(forming),从列写(reset)
        """
        self.clear_dac_v()
        self.op_mode = "write"
        self.write_from_row = row
        if self.write_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(1)),                                                  # 配置行到施加电压
                CMD(COL_CTRL,command_data=CmdData(0)),                                                  # 配置列到TIA
                CMD(ROW_COL_SW,command_data=CmdData(1)),                                                # PCB上的TIA接在列
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(ROW_CTRL,command_data=CmdData(0)),                                                  # 配置行到TIA
                CMD(COL_CTRL,command_data=CmdData(1)),                                                  # 配置列到电压
                CMD(ROW_COL_SW,command_data=CmdData(0)),                                                # PCB上的TIA接在行
            ],mode=1)
            self.ps.send_packets(pkts,delay=delay)

    def set_dac_write_V(self,v:float,tg_v:float = 5):
        """
            配置dac的读电压
        """
        self.write_voltage = v
        if self.deviceType==0:
            if self.write_from_row:
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             #

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             #
                self.dac.set_voltage(tg_v,dac_num=0,dac_channel=6)          # TG
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             #  
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             #
            else:   
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             #

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             #
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             #
                self.dac.set_voltage(tg_v,dac_num=0,dac_channel=6)             # TG
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             #

                self.dac.set_voltage(v,dac_num=1,dac_channel=0)             # ROW_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             #    
                self.dac.set_voltage(v,dac_num=1,dac_channel=2)             # COL_Va
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             #
        elif self.deviceType==1:    
            if self.write_from_row:  
                self.dac.set_voltage(v,dac_num=0,dac_channel=0)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=1)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=2)             # ROW_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=3)             # ROW_Va电压

                # self.dac.set_voltage(0,dac_num=0,dac_channel=4)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=5)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=6)             # COL_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=7)             # COL_Va电压

                # self.dac.set_voltage(0,dac_num=1,dac_channel=0)             # ROW_Vc
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             # COL_Vc     
                # self.dac.set_voltage(0,dac_num=1,dac_channel=2)             # GL
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             # GR
            else:   
                # self.dac.set_voltage(0,dac_num=0,dac_channel=0)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=1)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=2)             # ROW_Va电压
                # self.dac.set_voltage(0,dac_num=0,dac_channel=3)             # ROW_Va电压

                self.dac.set_voltage(v,dac_num=0,dac_channel=4)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=5)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=6)             # COL_Va电压
                self.dac.set_voltage(v,dac_num=0,dac_channel=7)             # COL_Va电压

                # self.dac.set_voltage(0,dac_num=1,dac_channel=0)             # ROW_Vc
                # self.dac.set_voltage(0,dac_num=1,dac_channel=1)             # COL_Vc     
                # self.dac.set_voltage(0,dac_num=1,dac_channel=2)             # GL
                # self.dac.set_voltage(0,dac_num=1,dac_channel=3)             # GR

    def set_write(self, row:bool, v:float, gain:int, tg_v:float = 5):
        """
            封装
        """
        self.set_write_mode(row=row)
        self.set_dac_write_V(v,tg_v=tg_v) 

    def generate_write_pulse(self, pulse_width = 1e-6):
        """
            产生写脉冲
        """
        self.pulse_cyc = int(pulse_width/self.pulse_cyc_length)
        if self.write_from_row:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，配置列为常1
                
                CMD(PULSE_CYC,command_data=CmdData(self.pulse_cyc)),            # 设置脉宽
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),             # cfg_row_pulse, 给写脉冲

                CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，读完后，把列电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)
        else:
            pkts=Packet()
            pkts.append_cmdlist([
                CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),             # cfg_row_pulse，配置行为常1

                CMD(PULSE_CYC,command_data=CmdData(self.pulse_cyc)),            # 设置脉宽
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse, 给写脉冲

                CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
                CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),             # cfg_row_pulse，读完后，把行电压翻转为0
            ],mode=1)
            self.ps.send_packets(pkts)

    def write_one(self,row_index:int,col_index:int,pulse_width:float):
        """
            读某一个器件，row_index为行索引，col_index为列索引
        """
        self.pulse_cyc = int(pulse_width/self.pulse_cyc_length)
        print(self.get_setting_info())
        assert self.op_mode == "write","未设置为写模式。"
        assert self.write_voltage is not None,"未设置写电压。"

        if not self.write_from_row:
            row_index, col_index = col_index, row_index
        self.set_cim_reset()                                                                        # 先reset 
        self.set_latch([[row_index]],row=self.write_from_row,value=None)                             # 配置行
        self.set_latch([[col_index]],row=not self.write_from_row,value=None)                         # 配置列
        self.generate_write_pulse(pulse_width)                                                      # 产生写脉冲

    def write_one_dG(self,x, y, write_voltage=5, pulsewidth=255*10*1e-9, dG=1e-3, dGperPulse=1e-5, eRate=0.01, maxWrite=10):
        """
            写一个器件
            注意: x和y都是从0索引开始
        """
        # 设置为写模式
        self.change_operation_mode("write")

        # 配置行列的latch
        self.cfg_row_col_one(x,y)

        # 设置电压
        self.set_voltage(write_voltage)

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，常1
            CMD(PULSE_CYC,command_data=CmdData(int(pulsewidth/self.pulse_cyc_length))),             # 设置脉宽
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_pulse)),             # cfg_row_pulse, 给写脉冲
            CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转回来
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，写完后，把列电压置0
        ],mode=1)
        self.ps.send_packets(pkts)
    

    def close(self):
        """
            关闭TCP连接
        """
        self.ps.close()


    #------------------------------------------------------------------------------------------
    # ************************************* 新版加速代码 ***************************************
    #------------------------------------------------------------------------------------------

    #------------------------------------------------------------------------------------------
    # *************************************** 其他操作 *****************************************
    #------------------------------------------------------------------------------------------
    def set_op_mode2(self,read=True,row=True):
        """
            设置操作模式
        """
        if read:
            self.op_mode = "read"
            self.read_from_row = row
        else:
            self.op_mode = "write"
            self.write_from_row = row
    
    #------------------------------------------------------------------------------------------
    # *************************************** DAC配置 *****************************************
    #------------------------------------------------------------------------------------------

    def clear_dac_v2(self):
        """
            清除dac的电压
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

    def get_read_dac_ins2(self,v,tg=5):
        """
            得到读器件的配置dac的指令
        """
        cmd=[]
        if self.deviceType==0:                      # ReRAM
            for i in DAC_INFO.RERAM_TG:
                cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(tg))))
            if self.read_from_row:                  # 从行读
                for i in DAC_INFO.RERAM_ROW_VA:
                    cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
            else:                                   # 从列读
                for i in DAC_INFO.RERAM_COL_VA:
                    cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
        elif self.deviceType==1:                    # ECRAM
            if self.read_from_row:                  # 从行读
                for i in DAC_INFO.ECRAM_ROW_VA:
                    cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
            else:                                   # 从列读
                for i in DAC_INFO.ECRAM_COL_VA:
                    cmd.append(CMD(PL_DAC_V,command_data=CmdData((i+DAC_INFO.INDEX_START)<<16 | self.dac.VToBytes(v))))
        return cmd
    
    #------------------------------------------------------------------------------------------
    # ************************************** 读相关函数 ****************************************
    #------------------------------------------------------------------------------------------

    def send_din_ram2(self,row_index:list,col_index:list,din_ram_start=0,tia_flag=True):
        """
            发送配置行列latch需要的数据
        """
        # (k,v,bank,index,tia)
        din_ram_pos = din_ram_start
        # --------------------------------------------------准备din_ram的数据
        din_ram_data = []                                   # 要发送下去的数据
        res_row_bank = []                                   # 等会配行bank指令执行需要的数据，单层list
        res_col_bank = []                                   # 等会配列bank指令执行需要的数据，双层list
        res_col_tia  = []                                   # 需要读出tia的值，双层list

        # --------------------------------------------------行数据映射--------------------------------------------------
        row_data = self.get_bank_tia(row_index)
        # --------------------------------------------------映射8个bank
        row_bank = [[] for _ in range(8)]
        for i in row_data:
            row_bank[i[2]].append(i[1])
        row_bank = [i for i in row_bank if len(i)>0]
        # --------------------------------------------------填入数据
        for i in row_bank:
            bank,index = self.get_data(i)
            din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index)))
            # 对应bank，以及对应的din_ram的地址
            res_row_bank.append((bank,din_ram_pos))       # bank，对应的32值存在din_ram_start位置
            din_ram_pos = din_ram_pos+1

        # (k,v,bank,index,tia)
        # --------------------------------------------------列数据映射--------------------------------------------------
        col_data = self.get_bank_tia(col_index)
        if not tia_flag:
            col_tmp = []
            # ----------------------------------------------映射8个bank
            col_bank = [[] for _ in range(8)]
            for i in col_data:
                col_bank[i[2]].append(i[1])
            col_bank = [i for i in col_bank if len(i)>0]
            # ----------------------------------------------填入数据
            for i in col_bank:
                bank,index = self.get_data(i)
                din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index)))
                # 对应bank，以及对应的din_ram的地址
                col_tmp.append((bank,din_ram_pos))        # bank，对应的32值存在din_ram_start位置
                din_ram_pos = din_ram_pos+1
            # ----------------------------------------------返回的数据，用于指令的执行
            res_col_bank.append(col_tmp)

            # ----------------------------------------------返回的数据，用于TIA的输出映射
            res_col_tia.append([(i[0],i[4]) for i in col_data])         # 第i[0]列，第i[4]路TIA 
        else:
            # (k,v,bank,index,tia)
            # ----------------------------------------------映射16路tia
            tia16 = [[] for _ in range(16)]
            for i in col_data:
                tia16[i[4]].append(i)
            # ----------------------------------------------每路TIA选一路
            flag = True
            read_num = []                                   # 两层list，每个元素为list，表示一列对应一路tia的数据
            while flag:
                flag = False
                tmp = []
                for i in tia16:
                    if len(i)>0:
                        tmp.append(i.pop())                     # 每路tia选一个值
                        flag = True
                if flag == True:                            # 有值才加进去
                    read_num.append(tmp)
            # ----------------------------------------------循环去读，也就是循环去配置列的latch
            for i in read_num:
                col_tmp = []
                # (k,v,bank,index,tia)
                # ------------------------------------------映射8个bank
                col_bank = [[] for _ in range(8)]
                for j in i:
                    col_bank[j[2]].append(j[1])
                col_bank = [j for j in col_bank if len(j)>0]
                # ------------------------------------------填入数据
                for j in col_bank:
                    bank,index = self.get_data(j)
                    din_ram_data.append(CMD(PL_DATA,command_data=CmdData(index)))
                    # 对应bank，以及对应的din_ram的地址
                    col_tmp.append((bank,din_ram_pos))
                    din_ram_pos = din_ram_pos+1
                # ------------------------------------------返回的数据，用于指令的执行
                res_col_bank.append(col_tmp)

                # ------------------------------------------返回的数据，用于TIA的输出映射
                res_col_tia.append([(j[0],j[4]) for j in i] )       # 第j[0]列，第j[4]路TIA

        # 发送din_ram数据
        din_ram_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(len(din_ram_data))))      # 有多少条数据
        assert len(din_ram_data)+din_ram_start < 256,"send_din_ram：din_ram超过界限。"
        din_ram_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(din_ram_pos)))             # 数据从哪开始

        pkts=Packet()
        pkts.append_single(din_ram_data,mode=5)
        self.ps.send_packets(pkts)
        # 然后根据返回的信息，构建读指令

        return res_row_bank,res_col_bank,res_col_tia
    
    def read2(self,row_index:list,col_index:list,read_voltage:float,tg:float = 5,tia_flag = True, get_tia16 = False):
        """
            读器件，row_index为行索引，col_index为列索引
        """
        assert self.op_mode == "read","未设置为读模式。"

        self.read_voltage = read_voltage
        print(self.get_setting_info())
        # ----------------------------------------------从行还是列去读
        if self.read_from_row:
            # 从行读
            row_bank_ins, col_bank_ins =  PL_ROW_BANK, PL_COL_BANK
            read_ins = PL_READ_ROW_PULSE
        else:
            # 从列读
            row_index, col_index = col_index, row_index
            row_bank_ins, col_bank_ins =  PL_COL_BANK, PL_ROW_BANK
            read_ins = PL_READ_COL_PULSE

        # ----------------------------------------------ins_ram,din_ram,dout_ram的地址
        ins_ram_start = 0
        din_ram_start = 0
        dout_ram_start = 0
        dout_ram_pos = dout_ram_start

        # ----------------------------------------------发送要配置的bank的数据进去
        res_row_bank,res_col_bank,res_col_tia = self.send_din_ram2(row_index,col_index,din_ram_start,tia_flag)

        # ----------------------------------------------准备指令序列
        ins_data = self.get_read_dac_ins2(v=read_voltage,tg=tg)                                      # 配置电压

        for col in res_col_bank:
            for bank,din_ram_pos in res_row_bank:
                ins_data.append(CMD(row_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank

            for bank,din_ram_pos in col:
                ins_data.append(CMD(col_bank_ins,command_data=CmdData(bank<<8|din_ram_pos)))        # 从din_ram的din_ram_pos位置取数据配置bank

            ins_data.append(CMD(read_ins,command_data=CmdData(dout_ram_pos)))                       # 读脉冲，并将16路TIA的值存在dout_ram的dout_ram_pos位置
            dout_ram_pos = dout_ram_pos + 1

        num = len(ins_data)
        ins_data.insert(0,CMD(PL_DATA_LENGTH,command_data=CmdData(num)))
        ins_data.insert(0,CMD(PL_RAM_ADDR,command_data=CmdData(ins_ram_start)))

        # ----------------------------------------------发送指令序列并执行
        pkts=Packet()
        pkts.append_single(ins_data,mode=4)
        pkts.append_single([CMD(INS_NUM,command_data=CmdData(num))],mode=1)
        pkts.append_single([CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_ins_run))],mode=1)
        self.ps.send_packets(pkts)

        vres,cres = self.adc.get_tia_out(num=len(res_col_bank),dout_ram_start=0,read_voltage=read_voltage)
        # vres = [[i for i in range(16)] for j in range(16)]
        # cres = [[i for i in range(16)] for j in range(16)]
        if get_tia16:
            # 直接返回16路TIA的值
            return np.array(vres),np.array(cres)
        else:
            vres_list,cres_list = [0]*len(col_index),[0]*len(col_index)
            # ----------------------------------------------读TIA的值
            for i,v in enumerate(res_col_tia):
                for _,v2 in enumerate(v):
                    # v2中数据 (第j[0]列，第j[4]路TIA)
                    vres_list[v2[0]]=vres[i][v2[1]]
                    cres_list[v2[0]]=cres[i][v2[1]]

            return np.array(vres_list),np.array(cres_list)