from cimCommand import CMD,CmdData,Packet
from cimCommand.singleCmdInfo import *
from pc import PS

class DAC():
    """
        针对DAC的一些操作
    """
    referenceVoltage = 2.5                  # 参考电压2.5v
    broadcast = True                        # 关闭broadcast
    gain = 1                                # 增益
    base = 2**12-1

    dac_spi_div = 4
    dac_ctr = 0xfff

    ps = None

    def __init__(self,ps:PS):
        self.ps = ps
        # DAC的初始化操作
        self.initOp()

    def initOp(self):
        """
            两个DAC, 需要关broadcast,以及将gain置2
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(DAC_IN,command_data=CmdData(0<<24|0x020000)),       # 关闭DAC的broadcast
            CMD(FAST_COMMAND_1,command_data=CmdData(1)),            # cfg_dac

            CMD(DAC_IN,command_data=CmdData(0<<24|0x0400ff)),       # DAC的每个通道gain都置2, 1表示增益为2,0表示增益为1
            CMD(FAST_COMMAND_1,command_data=CmdData(1)),            # cfg_dac

            CMD(DAC_IN,command_data=CmdData(1<<24|0x020000)),       # 关闭DAC的broadcast
            CMD(FAST_COMMAND_1,command_data=CmdData(1)),            # cfg_dac

            CMD(DAC_IN,command_data=CmdData(1<<24|0x0400ff)),       # DAC的每个通道gain都置2
            CMD(FAST_COMMAND_1,command_data=CmdData(1)),            # cfg_dac
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)

        self.broadcast = False
        self.gain = 2

    def set_voltage(self,v,dac_num:int,dac_channel:int):
        """
            将第dac_num的DAC的第dac_channel通道设置为对应的电压值
            dac_num从0开始
            dac_channel从0开始
        """
        pkts=Packet()
        dac_num = dac_num<<24
        dac_channel = (dac_channel+8)<<16
        vbits = self.VToBytes(v)
        pkts.append_cmdlist([
            CMD(DAC_IN,command_data=CmdData(dac_num|dac_channel|vbits)),                    # 设置dac的dac_c通道电压为vbits对应的值
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_dac)),           # cfg_dac
        ],mode=1)

        self.ps.send_packets(pkts)

    def set_spi_div(self,dac_spi_div = 2,):
        """
            设置DAC的工作频率？
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(DAC_SPI_DIV,command_data=CmdData(dac_spi_div)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)
        self.dac_spi_div = dac_spi_div

    def set_dac_ctr(self,dac_ctr = 0x0fff):
        """
            设置DAC的工作频率？
        """
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(DAC_CTR,command_data=CmdData(dac_ctr)),
        ],mode=1)

        # 发送指令
        self.ps.send_packets(pkts)
        self.dac_ctr = dac_ctr

    def set_flt(self,data):
        pkts=Packet()
        pkts.append_cmdlist([
            CMD(FLT,command_data=CmdData(data)),                  # 配置flt
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le1)),         # cfg_flt_le1
            CMD(FAST_COMMAND_1,command_data=CmdData(FAST_COMMAND1_CONF.cfg_flt_le2)),         # cfg_flt_le2
        ],mode=1)
        self.ps.send_packets(pkts)

    # def get_out(self):
    #     """
    #         读DAC？
    #     """
    #     pkts=Packet()
    #     pkts.append_cmdlist([
    #         CMD(DAC_OUT),
    #     ],mode=2)

    #     # 发送指令
    #     self.ps.send_packets(pkts)
    #     # 接收信息
    #     # DAC寄存器回读值。高8bit: 0,低24bit: DAC寄存器的24bit值
    #     meessage = self.ps.receive_packet()
    #     return meessage

    def VToBytes(self,v):
        """
            将需求的DAC电压转成16bit, 对应的电压bit
        """
        assert v <= self.referenceVoltage*self.gain,"VToBytes: 电压超过范围!"
        res = v/self.referenceVoltage/self.gain*self.base
        return int(res)<<4