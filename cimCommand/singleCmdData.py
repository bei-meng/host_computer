class CmdData:
    """
        data: 存储的对应指令的需要的数据
    """
    data = 0
    # big

    def __init__(self, data:int = 0)->None:
        """
            初始化数据
        """
        self.data = data
    
    def __str__ (self):
        """
            输出数据的相关信息
        """
        result=f"数据:\t{self.data}\n字节:\t{str(bytes(self))}"
        return result
    
    def set_data(self,data:int):
        """
            设置命令的数据
        """
        self.data=data
    
    def get_data(self):
        """
            获取命令的数据
        """
        return self.data
    
    def set_bit(self, pos:int, newdata:int):
        """
            将数据中的第pos位设置为newdata
        """
        mask=1
        mask<<=pos
        mask=~mask
        self.data = self.data&mask|(newdata<<pos)

    def replace_bit(self, start:int, length:int, newdata:int):
        """
            将数据中起始位置为start位, 长度为length的比特, 替换为newdata对应的数据
        """
        mask=0
        for i in range(length):
            mask<<=1
            mask|=1
        # 超过长度的截断
        newdata&=mask

        mask<<=start
        mask=~mask

        self.data = self.data&mask|(newdata<<start)