import numpy as np
from scipy.sparse import lil_matrix

"""
现在都是从列给信号,行输出电流,能避免sneak path的问题,但是不能避免IR下降问题,还有外面线阻的影响
开一列,开的行越多,电流越大,IR下降影响越大
"""


class crossbar_array:
    net_size = None  # 元组(行数,列数)
    col_select = None  # 选择的列
    row_select = None  # 选择的行
    R_wire = None  # 单位导线点阻
    R_in = None  # 输入端电阻
    R_out = None  # 输出端电阻

    def __init__(self, R_wire, R_in, R_out):
        self.R_wire = R_wire
        self.R_in = R_in
        self.R_out = R_out

    def set_array(self, net_size, col_select, row_select):
        self.net_size = net_size
        self.col_select = col_select
        self.row_select = row_select

    def set_corssbar(self, R_wire, R_in, R_out):
        self.R_wire = R_wire
        self.R_in = R_in
        self.R_out = R_out


def calculate_g_effective(array_obj: crossbar_array, G_read_slow, V_in):
    """
    计算 有效电导矩阵G, 模拟所给阵列的输出

    Parameters:
        array_obj: 阵列配置
        G_read_slow: 读出的电导矩阵
        V_in: 输入的电压向量

    Returns:
        G_eff: 相对输入的实际有效电导矩阵
        I_simu: 模拟电流,表示在给定输入电压下
    """

    M, N = array_obj.net_size

    R_upper = np.array([(array_obj.col_select[0] - 1) * array_obj.R_wire + array_obj.R_in]
                       +list(np.diff(array_obj.col_select) * array_obj.R_wire))
    R_lower = np.array([(array_obj.col_select[0] - 1) * array_obj.R_wire + array_obj.R_in]
                       +list(np.diff(array_obj.col_select) * array_obj.R_wire))
    
