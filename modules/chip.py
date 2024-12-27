from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS
from modules.adc import ADC
from modules.dac import DAC

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


    ps = None
    adc = None
    dac = None

    mode = "None"

    def __init__(self, adc:ADC, dac:DAC, ps:PS):
        self.ps = ps
        self.adc = adc
        self.dac = dac

        # DAC的初始化操作
        self.initOp()

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
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)


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


    def change_operation_mode(self,mode="read"):
        """
            操作模式, 行和列接到不同的设置
        """
        
        if mode=="read" and self.mode!=mode:
            pkts=Packet()
            if self.deviceType == 0 :
                pkts.append_cmdlist([
                    CMD(ROW_CTRL,command_data=CmdData(1)),                  # 配置行到施加电压
                    CMD(COL_CTRL,command_data=CmdData(0)),                  # 配置列到TIA  
                ])
            self.mode="read"
            self.ps.send_packets(pkts)
        elif mode =="write" and self.mode!=mode:
            pkts=Packet()
            if self.deviceType == 0 :
                pkts.append_cmdlist([
                    CMD(ROW_CTRL,command_data=CmdData(1)),                  # 配置行到施加电压
                    CMD(COL_CTRL,command_data=CmdData(0)),                  # 配置列到施加电压 
                ])
            self.mode="write"
            self.ps.send_packets(pkts)

    def cfg_row_col_one(self,x:int,y:int):
        """
            配置行和列的latch数据
        """
        # 数据准备
        xbank,xindex = self.numToBank_Index(x)
        ybank,yindex = self.numToBank_Index(y)

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(CIM_RESET,command_data=CmdData(1)),                 # reset指令
            # 行reg配置
            CMD(CIM_DATA_IN,command_data=CmdData(1<<xindex)),       # 第xindex位置1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

            # 行bank配置
            CMD(ROW_COL_SEL,command_data=CmdData(1)),               # 设置为行模式
            CMD(CIM_BANK_SEL,command_data=CmdData(1<<xbank)),       # 行bank选择
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk

            # 列reg配置
            CMD(CIM_DATA_IN,command_data=CmdData(1<<yindex)),       # 第yindex位置1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_cim_data_in)),       # cfg_cim_data_in
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_reg_clk)),           # cfg_reg_clk

            # 列bank配置
            CMD(ROW_COL_SEL,command_data=CmdData(0)),               # 设置为列模式
            CMD(CIM_BANK_SEL,command_data=CmdData(1<<ybank)),       # 列bank选择
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_bank_sel)),          # cfg_bank_sel
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_latch_clk)),         # cfg_latch_clk
        ],mode=1)
        # 发送命令
        self.ps.send_packets(pkts)

    def set_voltage(self,voltage = 0.2):
        """
            根据读写模式以及器件类型执行dac的电压设置
        """
        if self.mode == "read":
            # 设置DAC电压
            if self.deviceType==1:
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # ROW_Va电压
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # ROW_Vc电压
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # COL_Vc电压
            elif self.deviceType==0:
                self.dac.set_voltage(voltage,dac_num=1,dac_channel=0)           # ROW_Va电压，第一个DAC，第0个通道
                self.dac.set_voltage(5,dac_num=0,dac_channel=6)                 # TG,默认5v，第0个DAC，第6个通道
        elif self.mode == "write":
            # 设置DAC电压
            if self.deviceType==1:
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # ROW_Va电压
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # ROW_Vc电压
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # COL_Vc电压
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # GL
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # GR
            elif self.deviceType==0:
                self.dac.set_voltage(2,dac_num=0,dac_channel=0)                 # ROW_Va电压，2v
                self.dac.set_voltage(voltage,dac_num=0,dac_channel=0)           # TG

    def read_one(self,x,y,read_voltage=0.1, sample_point_num=32):
        """
            读一个器件
            注意: x和y都是从0索引开始
        """
        # 配置行列的latch
        self.cfg_row_col_one(x,y)

        # 设置为read模式
        self.change_operation_mode("read")

        # 设置read模式下的相关DAC电压
        self.set_voltage(read_voltage)

        # 设置PCB的TIA，为列
        self.adc.set_row_col_sw(1)

        # 设置ADC采样点数
        self.adc.set_sample_times(sample_point_num)

        pkts=Packet()
        pkts.append_cmdlist([
            CMD(PULSE_CYC,command_data=CmdData(0)),                                                 # 翻转
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，配置列为常1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_row_read)),              # 然后开始读
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_col_pulse)),             # cfg_col_pulse，读完后，把列电压翻转为0
        ],mode=1)
        self.ps.send_packets(pkts)

        # 从第y列的ADC读出来
        message=self.adc.get_out(y,device=self.deviceType)
        return message
    
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