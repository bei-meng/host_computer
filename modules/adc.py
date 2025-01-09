from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS

class ADC():
    """
        针对ADC的一些操作
    """
    channel_num = 4
    adc_spi_div = 2
    adc_sample_times = 32
    adc_first_gap = 0xa
    adc_last_gap = 0xa
    adc_cs_gap = 0x0190
    gain = 0

    row_col_sw = 0 

    ps = None

    def __init__(self,ps:PS):
        self.ps = ps
        # DAC的初始化操作
        self.initOp()

    def initOp(self):
        """
            将ADC配置为4通道
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ADC0_IN,command_data=CmdData(0xA200)),                                          # 配置ADC为四通道
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_adc0)),              # cfg_adc0

            CMD(ADC1_IN,command_data=CmdData(0xA200)),                                          # 配置ADC为四通道
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_adc1)),              # cfg_adc1

            CMD(ADC2_IN,command_data=CmdData(0xA200)),                                          # 配置ADC为四通道
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_adc2)),              # cfg_adc2

            CMD(ADC3_IN,command_data=CmdData(0xA200)),                                          # 配置ADC为四通道
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_adc3)),              # cfg_adc3
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)
        self.channel_num = 4

    def set_row_col_sw(self,row_col_sw = 0):
        """
            pcb上row或col的TIA，0:row,1:col
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ROW_COL_SW,command_data=CmdData(row_col_sw)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)
        self.row_col_sw = row_col_sw
    

    def set_spi_div(self,adc_spi_div = 2,):
        """
            设置ADC的工作频率?
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ADC_SPI_DIV,command_data=CmdData(adc_spi_div)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)
        self.adc_spi_div = adc_spi_div

    def set_sample_times(self,adc_sample_times = 32):
        """
            设置ADC的采样次数
        """
        assert adc_sample_times>=1 and adc_sample_times<=32, "set_sample_times: ADC采样次数超过界限! "
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ADC_SAMPLE_TIMES,command_data=CmdData(adc_sample_times)),                           # 配置ADC的采样次数
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

        self.adc_sample_times=adc_sample_times

    def set_gap(self,adc_cs_gap = None,adc_first_gap = None,adc_last_gap = None):
        """
            设置ADC延迟相关参数
        """
        self.adc_cs_gap=self.adc_cs_gap if adc_cs_gap is None else adc_cs_gap
        self.adc_first_gap=self.adc_first_gap if adc_first_gap is None else adc_first_gap
        self.adc_last_gap=self.adc_last_gap if adc_last_gap is None else adc_last_gap
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(ADC_FIRST_GAP,command_data=CmdData(self.adc_first_gap)),
            CMD(ADC_CS_GAP,command_data=CmdData(self.adc_cs_gap)),
            CMD(ADC_LAST_GAP,command_data=CmdData(self.adc_cs_gap)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)


    def set_gain(self,gain,delay=None):
        """
            设置ADC的增益?
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(GAIN,command_data=CmdData(gain)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts,delay=delay)
        self.gain=gain

    def get_out(self,num:list,read_voltage:float,delay=None):
        """
            从adc_num的adc的adc_channel读数据
        """
        message_cond = []
        message_v = []
        for TIA_num in num:
            adc_num, adc_channel = int(TIA_num/4),TIA_num%4

            channel_map = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}
            pkts=Packet()
            adc_out = CMD(dict(
                command_addr = 65+TIA_num,
                command_type = COMMAND_TYPE[1],
                n_addr_bytes = N_ADDR_BYTES[0],
                n_data_bytes = N_DATA_BYTES[0],
                command_name = f"adc{adc_num}_out{channel_map[adc_channel]}",
                command_data = CmdData(0),
                command_description = "从ADC对应通道读取数据"
            ))
            pkts.append_cmdlist([adc_out],mode=2)

            # 发送指令
            self.ps.send_packets(pkts,delay=delay)
            # 接收信息
            # 高16bit：0，低16bit：寄存器的16bit值
            message = self.ps.receive_packet(f"adc读取:{adc_out.command_name}")
            message_cond.append(self.adc_to_cond(message, read_voltage))
            message_v.append(self.adc_to_voltage(message))
        return message_cond,message_v
    
    def adc_to_voltage(self,message, vref=1.25):
        """
            读取的值换算成电压
        """
        voltage_sample_hex = message.hex()[2:4] + message.hex()[0:2]
        # 将十六进制字符串转换为整数
        data = int(voltage_sample_hex, 16)
        # 确保数据在16位范围内
        data &= 0xFFFF
        # 将16位有符号数转换为Python整数
        if data & 0x8000:  # 若符号位为1，则表示负数
            data -= 0x10000

        # 将数据转换为电压
        voltage = (data / (2**15-1)) * vref  # 32767 是0x7FFF对应的正最大值
        return voltage
    
    def adc_to_cond(self,message,read_voltage,vref=1.25):
        """
            读取的值换算成电导(单位:us)
        """
        voltage = self.adc_to_voltage(message,vref)
        # 返回的单位是us
        if self.gain == 0:
            return voltage/((read_voltage+1e-10)*6.0241*(10e3+200))*1e6
        elif self.gain == 1:
            return voltage/((read_voltage+1e-10)*1*(10e3+200))*1e6
        elif self.gain == 2:
            return voltage/((read_voltage+1e-10)*6.0241*200)*1e6
        elif self.gain == 3:
            return voltage/((read_voltage+1e-10)*1*200)*1e6
    

    def TIA_index_map(self,num,device=0,col=True):
        """
            注意：num从0索引开始
            将对应的行或列索引映射为对应的TIA偏移
        """
        num += 1
        assert num > 0 and num < 257,"numToBank_Index: num超过范围!"
        if device==0 and col:
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
