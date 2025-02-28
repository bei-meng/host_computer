from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS


class CLK_MANAGER():
    op_bank_cfg_done_delay_cyc = 1000
    op_cim_data_cfg_done_delay_cyc = 1000
    reg_clk_done_delay_cyc = 1000
    latch_clk_done_delay_cyc = 1000
    op_adc_avrg_done_delay_cyc = 1000
    op_dac_cfg_done_delay_cyc = 1000
    op_row_pulse_done_delay_cyc = 1000
    op_col_pulse_done_delay_cyc = 1000
    op_cim_rstn_done_delay_cyc = 1000

    cim_rstn_cyc = 1000                                             # 负脉冲，低电平cycle数，1 cycle=10ns，指令模式下reset的宽度 0：翻转
    latch_clk_cyc = 1000                                            # 正脉冲, 高电平cycle数, 1 cycle=10ns 0: 翻转
    reg_clk_cyc = 1000                                              # 正脉冲, 高电平cycle数, 1 cycle=10ns 0: 翻转
    latch_cyc = 1000                                                # 正脉冲, PCB上锁存器的latch cycle数

    pulse_cyc = 256                                                 # row/col pulse的cycle数 0: 翻转"

    # latch_cyc = 0x2                 # PCB上锁存器的latch cycle树
    # reg_clk_cyc = 0xF               # 高电平cycle数, 1 cycle=10ns 0: 翻转
    # latch_clk_cyc = 0xF             # 高电平cycle数, 1 cycle=10ns 0: 翻转
    # cim_rstn_cyc = 0xF              # cim

    ps = None
    
    init = True

    def __init__(self,ps:PS,init = True):
        self.ps = ps
        self.init = init
        self.set_cyc()

    def set_pulse_cyc(self,pulsewidth:float):
        pulse_cyc=int(pulsewidth/PULSE_CYC_LENGTH)
        assert pulse_cyc>=0 ,"set_pulse_width: 脉宽超过界限！"

        pkts=Packet()
        pkts.append_cmdlist([CMD(PULSE_CYC,command_data=CmdData(pulse_cyc)),],mode=1)
        self.ps.send_packets(pkts)

        self.pulse_cyc = pulse_cyc

    def set_cyc(self,delay1 = 10,delay2 = 100):        
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(OP_BANK_CFG_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_CIM_DATA_CFG_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(REG_CLK_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(LATCH_CLK_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_ADC_AVRG_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_DAC_AVRG_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_ROW_PULSE_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_COL_PULSE_DONE_DELAY_CYC,command_data=CmdData(delay1)),
            CMD(OP_CIM_RSTN_DONE_DELAY_CYC,command_data=CmdData(delay1)),

            CMD(CIM_RSTN_CYC,command_data=CmdData(delay2)),
            CMD(LATCH_CLK_CYC,command_data=CmdData(delay2)),
            CMD(REG_CLK_CYC,command_data=CmdData(delay2)),
            CMD(LATCH_CYC,command_data=CmdData(delay2)),
        ],mode=1)
        self.ps.send_packets(pkts)
