"""
    命令的相关数据

    command_addr: 命令的地址
    command_type: 命令的类型

    n_addr_bytes: 命令的地址字节数
    n_data_bytes: 命令的数据字节数

    command_name: 命令的名称
    command_data: 命令的数据
    command_description: 对命令功能的描述
"""

from cimCommand.singleCmdData import CmdData
#-------------------------------------------------------------------备选参数
PACKET_MODS  = [0,1,2,3,4,5]                # 四个模式
N_ADDR_BYTES = [1,0]                        # 命令的地址占几个字节
N_DATA_BYTES = [4,3,2,1]                    # 命令的数据占几个字节,3,2是后面加的，为了不打乱前面的顺序
COMMAND_TYPE = ["RW","ROI","PL"]            # 命令的类型是什么
COMMAND_ADDR = 0                            # 命令的地址
BYTE_ORDER   = "big"                        # 命令转换为字节后的字节序，or "big"


class FAST_COMMAND1_CONF():
    """ 
        fast_command_1 32bit 控制字配置
    """

    cfg_dac = 1<<0
    cfg_adc0 = 1<<1
    cfg_adc1 = 1<<2
    cfg_adc2 = 1<<3
    cfg_adc3 = 1<<4
    cfg_cim_data_in = 1<<5
    cfg_bank_sel = 1<<6
    cfg_flt_le1 = 1<<7
    cfg_flt_le2 = 1<<8
    
    cfg_reg_clk = 1<<9
    cfg_pos_reg_clk = 1<<9
    
    cfg_latch_clk = 1<<10
    cfg_row_pulse = 1<<11
    cfg_col_pulse = 1<<12
    cfg_row_read = 1<<13
    cfg_col_read = 1<<14
    cfg_ins_run = 1<<15
    
    negative_reg_clk = 1<<31


#-------------------------------------------------------------------FAST_COMMAND_0:0
FAST_COMMAND_0=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "fast_command_0",
    command_data = CmdData(0),
    command_description = 
    """触发PL运行某功能
        bit位   功能
        14	cfg_col_read	产生col read pulse脉冲，adc求平均返回寄存器
        13	cfg_row_read	产生row read pulse脉冲，adc求平均返回寄存器
        12	cfg_col_pulse	
        11	cfg_row_pulse	
        10	cfg_latch_clk	
        9	cfg_reg_clk	
        8	cfg_flt_le2	
        7	cfg_flt_le1	
        6	cfg_bank_sel	
        5	cfg_cim_data_in	配置32bit data
        4	cfg_adc3	配置ADC3
        3	cfg_adc2	配置ADC2
        2	cfg_adc1	配置ADC1
        1	cfg_adc0	配置ADC0
        0	cfg_dac	配置DAC"""
)

COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------FAST_COMMAND_1:1
FAST_COMMAND_1=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "fast_command_1",
    command_data = CmdData(0),
    command_description = "触发PL运行某功能"
)
COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------DAC_IN:2
DAC_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "dac_in",
    command_data = CmdData(0),
    command_description = "高8bit：0或1，选择dac。低24bit：spi写入DAC寄存器的24bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------ADC0_IN:3
ADC0_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc0_in",
    command_data = CmdData(0),
    command_description = "高16bit：0，低16bit，spi写入ADC寄存器的16bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------ADC1_IN:4
ADC1_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc1_in",
    command_data = CmdData(0),
    command_description = "高16bit：0，低16bit，spi写入ADC寄存器的16bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------ADC2_IN:5
ADC2_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc2_in",
    command_data = CmdData(0),
    command_description = "高16bit：0，低16bit，spi写入ADC寄存器的16bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1
#-------------------------------------------------------------------ADC3_IN:6
ADC3_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc3_in",
    command_data = CmdData(0),
    command_description = "高16bit：0，低16bit，spi写入ADC寄存器的16bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------DEVICE_CFG:7
DEVICE_CFG=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "device_cfg",
    command_data = CmdData(4),
    command_description = "见sheet：device_cfg"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------CIM_DATA_IN:8
CIM_DATA_IN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "cim_data_in",
    command_data = CmdData(0),
    command_description = "32bit data"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------FLT:9
FLT=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "flt",
    command_data = CmdData(0),
    command_description = "flt_oe,flt_group2[3:0],flt_group1[7:0]"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------CIM_BANK_SEL:10
CIM_BANK_SEL=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "cim_bank_sel",
    command_data = CmdData(0),
    command_description = "BA[7:0]"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------CIM_RESET:11
CIM_RESET=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "cim_reset",
    command_data = CmdData(0),
    command_description = "0或1"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------CIM_EN:12
CIM_EN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "cim_en",
    command_data = CmdData(0),
    command_description = "0或1 ?"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------CIM_SS:13
CIM_SS=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "cim_ss",
    command_data = CmdData(0),
    command_description = "0或1"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------SER_PARA_SEL:14
SER_PARA_SEL=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "ser_para_sel",
    command_data = CmdData(1),
    command_description = "0或1，0:串行,1:并行"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ROW_COL_SEL:15
ROW_COL_SEL=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "row_col_sel",
    command_data = CmdData(0),
    command_description = "0:col,1:row"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------GAIN:16
GAIN=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "gain",
    command_data = CmdData(0),
    command_description = "bit0:gain0_3v3,bit1:gain1_3v3"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ROW_COL_SW:17
ROW_COL_SW=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "row_col_sw",
    command_data = CmdData(0),
    command_description = "pcb上row或col的TIA，0:row,1:col"
)
COMMAND_ADDR+=1         # 命令的地址自增1


#-------------------------------------------------------------------DAC_CTR:18
DAC_CTR=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "dac_ctr",
    command_data = CmdData(0x0FFF),
    command_description = """CTR_A3-A6_W  	bit11
        CTR_A7-A10_W  	bit10
        CTR_A5-A8_E  	bit9
        CTR_A1-A4_E  	bit8
        CTR_A2-A5_N  	bit7
        CTR_A6-A9_N  	bit6
        CTR_A5-A8_S  	bit5
        CTR_A1-A4_S  	bit4
        CTR_A11_N	bit3
        CTR_A1_N	bit2
        CTR_A1-A2_W	bit1
        CTR_A10_N	bit0"""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ROW_CTRL:29
ROW_CTRL=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "row_ctrl",
    command_data = CmdData(0),
    command_description = ""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------COL_CTRL:20
COL_CTRL=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "col_ctrl",
    command_data = CmdData(0),
    command_description = ""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------DAC_CTR:21
DAC_SPI_DIV=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "dac_spi_div",
    command_data = CmdData(4),
    command_description = """spi_clk_freq = 100MHz / spi_div,默认25MHz。
        dac最快50MHz
        Spi_div最大值：1023"""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC_SPI_DIV:22
ADC_SPI_DIV=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc_spi_div",
    command_data = CmdData(2),
    command_description = """spi_clk_freq = 100MHz / spi_div,默认25MHz。
        adc最快50MHz
        Spi_div最大值：1023"""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC_SPI_DIV:23
ADC_CS_GAP=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc_cs_gap",
    command_data = CmdData(0x0190),
    command_description = """adc连续采样时，cs下降沿的间隔，最小250ns。
        adc默认cs宽度20ns X 16=320ns
        adc_cs_gap默认值400ns"""
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC_SAMPLE_TIMES:24
ADC_SAMPLE_TIMES=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc_sample_times",
    command_data = CmdData(32),
    command_description = "触发1次adc连续采样，adc采样的次数：1，2，4，8，16，32"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC_FIRST_GAP:25
ADC_FIRST_GAP=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc_first_gap",
    command_data = CmdData(0x000a),
    command_description = "adc的第一个cs下降沿和read pulse上升沿的间隔，默认100ns，10个cycle"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC_LAST_GAP:26
ADC_LAST_GAP=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc_last_gap",
    command_data = CmdData(0x000a),
    command_description = "adc的最后一个cs下降沿和read pulse下降沿升沿的间隔，默认100ns，10个cycle"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PULSE_CYC:27
PULSE_CYC=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "pulse_cyc",
    command_data = CmdData(256),
    command_description = "row/col pulse的cycle数（不和adc采样关联），0：翻转"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------INS_NUM:28
INS_NUM=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "ins_num",
    command_data = CmdData(0),
    command_description = "指令数量：1~1024，cfg_ins_run前配置"
)
COMMAND_ADDR+=1         # 命令的地址自增1


# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 


COMMAND_ADDR=30
#-------------------------------------------------------------------NEGTIVE_REG_CLK:30
NEGTIVE_REG_CLK=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[0],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "negtive_reg_clk",
    command_data = CmdData(0),
    command_description = ""
)
COMMAND_ADDR+=1         # 命令的地址自增1

# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 


COMMAND_ADDR =64
#-------------------------------------------------------------------DAC_OUT:64
DAC_OUT=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "dac_out",
    command_data = CmdData(0x000a),
    command_description = "DAC寄存器回读值。高8bit：0,低24bit：DAC寄存器的24bit值"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC0_OUT_A:65
ADC0_OUT_A=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc0_out_A",
    command_data = CmdData(0),
    command_description = "ADC0 A通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。Multi read时为平均值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC0_OUT_B:66
ADC0_OUT_B=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc0_out_B",
    command_data = CmdData(0),
    command_description = "ADC0 B通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC0_OUT_C:67
ADC0_OUT_C=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc0_out_C",
    command_data = CmdData(0),
    command_description = "ADC0 C通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC0_OUT_D:68
ADC0_OUT_D=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc0_out_D",
    command_data = CmdData(0),
    command_description = "ADC0 D通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC1_OUT_A:69
ADC1_OUT_A=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc1_out_A",
    command_data = CmdData(0),
    command_description = "ADC1 A通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC1_OUT_B:70
ADC1_OUT_B=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc1_out_B",
    command_data = CmdData(0),
    command_description = "ADC1 B通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC1_OUT_C:71
ADC1_OUT_C=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc1_out_C",
    command_data = CmdData(0),
    command_description = "ADC1 C通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC1_OUT_D:72
ADC1_OUT_D=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc1_out_D",
    command_data = CmdData(0),
    command_description = "ADC1 D通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC2_OUT_A:73
ADC2_OUT_A=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc2_out_A",
    command_data = CmdData(0),
    command_description = "ADC2 A通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC2_OUT_B:74
ADC2_OUT_B=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc2_out_B",
    command_data = CmdData(0),
    command_description = "ADC2 B通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC2_OUT_C:75
ADC2_OUT_C=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc2_out_C",
    command_data = CmdData(0),
    command_description = "ADC2 C通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC2_OUT_D:76
ADC2_OUT_D=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc2_out_D",
    command_data = CmdData(0),
    command_description = "ADC2 D通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC3_OUT_A:77
ADC3_OUT_A=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc3_out_A",
    command_data = CmdData(0),
    command_description = "ADC3 A通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC3_OUT_B:78
ADC3_OUT_B=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc3_out_B",
    command_data = CmdData(0),
    command_description = "ADC3 B通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC3_OUT_C:79
ADC3_OUT_C=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc3_out_C",
    command_data = CmdData(0),
    command_description = "ADC3 C通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------ADC3_OUT_D:80
ADC3_OUT_D=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[1],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[0],
    command_name = "adc3_out_D",
    command_data = CmdData(0),
    command_description = "ADC3 D通道寄存器回读值。高16bit：0，低16bit：寄存器的16bit值。"
)
COMMAND_ADDR+=1         # 命令的地址自增1




#------------------------------------------------------------------------------------------
# **************************************** PL指令 ******************************************
#------------------------------------------------------------------------------------------
PL_INS_RAM=dict(
    command_addr = 0,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[1],# 0
    n_data_bytes = N_DATA_BYTES[2],# 2
    command_name = "pl_ins_ram",
    command_data = CmdData(0),
    command_description = "ins ram起始地址"
)

PL_DATA_LENGTH=dict(
    command_addr = 0,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[1],# 0
    n_data_bytes = N_DATA_BYTES[2],# 2
    command_name = "pl_data_length",
    command_data = CmdData(0),
    command_description = "指令条数"
)

PL_DATA=dict(
    command_addr = 0,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[1],# 0
    n_data_bytes = N_DATA_BYTES[0],# 4
    command_name = "pl_data",
    command_data = CmdData(0),
    command_description = "数据"
)

WRITE_DIN_RAM=dict(
    command_addr = 0,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[1],# 0
    n_data_bytes = N_DATA_BYTES[2],# 2
    command_name = "read_din_ram",
    command_data = CmdData(0),
    command_description = "写din ram"
)

READ_DOUT_RAM=dict(
    command_addr = 0,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[1],# 0
    n_data_bytes = N_DATA_BYTES[2],# 2
    command_name = "read_dout_ram",
    command_data = CmdData(0),
    command_description = "读dout ram"
)





COMMAND_ADDR = 0x00

#-------------------------------------------------------------------PL_JUMP:0
PL_JUMP=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_jump",
    command_data = CmdData(0),
    command_description = "跳转"
)
COMMAND_ADDR+=1         # 命令的地址自增1


#-------------------------------------------------------------------PL_ROW_BANK:1
PL_ROW_BANK=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_row_bank",
    command_data = CmdData(0),
    command_description = "从din_ram读数据，配置32bit行寄存器"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_COL_BANK:2
PL_COL_BANK=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_col_bank",
    command_data = CmdData(0),
    command_description = "从din_ram读数据，配置32bit列寄存器"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_DAC_V:3
PL_DAC_V=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_dac_v",
    command_data = CmdData(0),
    command_description = "从din_ram读数据，配置32bit列寄存器"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_ROW_PULSE:4
PL_ROW_PULSE=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_row_pulse",
    command_data = CmdData(0),
    command_description = "产生row读pulse，求平均，16路并行写入dout_ram"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_COL_PULSE:5
PL_COL_PULSE=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_col_pulse",
    command_data = CmdData(0),
    command_description = "产生col读pulse，求平均，16路并行写入dout_ram"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_WRITE_ROW_PULSE:6
PL_WRITE_ROW_PULSE=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_write_row_pulse",
    command_data = CmdData(0),
    command_description = "产生row写pulse"
)
COMMAND_ADDR+=1         # 命令的地址自增1

#-------------------------------------------------------------------PL_WRITE_COL_PULSE:6
PL_WRITE_COL_PULSE=dict(
    command_addr = COMMAND_ADDR,
    command_type = COMMAND_TYPE[2],
    n_addr_bytes = N_ADDR_BYTES[0],
    n_data_bytes = N_DATA_BYTES[1],
    command_name = "pl_write_col_pulse",
    command_data = CmdData(0),
    command_description = "产生col写pulse"
)
COMMAND_ADDR+=1         # 命令的地址自增1