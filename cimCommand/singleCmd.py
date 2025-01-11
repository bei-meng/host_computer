from cimCommand.singleCmdInfo import (
    COMMAND_TYPE,
    N_ADDR_BYTES,
    N_DATA_BYTES,
    BYTE_ORDER
)
from cimCommand.singleCmdData import CmdData
class CMD:
    """
        command_addr: 命令的地址
        command_type: 命令的类型

        n_addr_bytes: 命令的地址字节数
        n_data_bytes: 命令的数据字节数

        command_name: 命令的名称
        command_data: 命令的数据
        command_description: 对命令功能的描述
    """
    command_addr = -1,
    command_type = COMMAND_TYPE.RW,

    n_addr_bytes = N_ADDR_BYTES.ONE,
    n_data_bytes = N_DATA_BYTES.FOUR,

    command_name = "None",
    command_data = CmdData(-1),
    command_description = "None"

    def __init__(self, data:dict,**kwargs)->None:
        """
            初始化命令的名字，类型，命令的地址长度，命令的数据长度
        """
        self.command_addr = data["command_addr"]
        self.command_type = data["command_type"]

        self.n_addr_bytes = data["n_addr_bytes"]
        self.n_data_bytes = data["n_data_bytes"]

        self.command_name = data["command_name"]
        self.command_data = data["command_data"]
        self.command_description = data["command_description"]

        for key, value in kwargs.items():
            assert hasattr(self,key),f"command 没有属性: {key}"
            setattr(self, key, value)

    def __bytes__(self):
        """
            将命令的地址和数据组合，转为对应长度的字节序列，字节序位小端"little"
        """
        return self.concatenate().to_bytes((self.n_addr_bytes + self.n_data_bytes), BYTE_ORDER)
    
    def __str__ (self):
        """
            输出命令相关信息
            # 字节序:\t{self.byte_order}\n
        """
        result=f"地址:\t{self.command_addr}\n类型:\t{self.command_type}\n位宽:\t{self.n_data_bytes*8} bit\n"
        result+=f"名字:\t{self.command_name}\n数据:\t{self.command_data.get_data()}\n"
        result+=f"字节:\t{str(bytes(self))}\n描述:\t{self.command_description}\n"
        return result
    
    def concatenate(self):
        """
            将命令的地址和数据进行移位组合
        """
        return (self.command_addr << (self.n_data_bytes * 8)) | self.command_data.get_data()
    
    def get_command(self):
        """
            获取命令的字节序列
        """
        return bytes(self)
    
    def get_addr(self,byte:bool=True):
        """
            获取地址的字节序列
        """
        if byte:
            return self.command_addr.to_bytes(self.n_addr_bytes , BYTE_ORDER)
        else:
            return self.command_addr
    
    def get_data(self,byte:bool=True):
        """
            获取数据的字节序列
        """
        if byte:
            return self.command_data.get_data().to_bytes(self.n_data_bytes , BYTE_ORDER)
        else:
            return self.command_data.get_data()
    
    def set_command(self, command_data:CmdData):
        """
            设置命令的数据
        """
        self.command_data = command_data