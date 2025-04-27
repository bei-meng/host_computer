import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np

import time
import json

def plot_v_cond(v,cond,figsize=(12,4),title=""):
    """
        绘制电压电导曲线图
    """
    plt.figure(figsize=figsize)
    plt.title = title

    plt.subplot(1,2,1)
    plt.plot(v,marker='o', linestyle='-', linewidth=2,label="voltage")
    plt.ylabel("voltage(v)")
    plt.xlabel("TIA")
    plt.legend()

    plt.subplot(1,2,2)
    plt.plot(cond,marker='o', linestyle='-', linewidth=2,label="cond")
    plt.ylabel("cond(us)")
    plt.xlabel("TIA")

    plt.legend()
    plt.show()


# def plot_cond(data,vmin = 0,vmax = 1400,title = "",label = "us",path = None):
#     """
#     :param data为256*256的np矩阵
#     """
#     # viridis， plasma， inferno， magma， cividis
#     # RdBu 、 RdYlBu 、 coolwarm 、 seismic
#     cmap = plt.cm.gray
#     norm = Normalize(vmin=vmin, vmax=vmax)
#     im = plt.imshow(data, cmap=cmap,norm=norm)
#     cbar = plt.colorbar(im)
#     cbar.set_label(label)
#     plt.title(title)
#     if path is not None:
#         plt.savefig(path)  # 保存为 PNG 格式
#     plt.show()


def plot_cond(data,vmin = 0,vmax = 1400,title = "",label = "us",path = None):
    """
    :param data为256*256的np矩阵
    """
    cmap = plt.cm.viridis
    norm = Normalize(vmin=vmin, vmax=vmax)
    im = plt.imshow(data, cmap=cmap,norm=norm)
    cbar = plt.colorbar(im)
    cbar.set_label(label)
    plt.title(title)
    if path is not None:
        plt.savefig(path)  # 保存为 PNG 格式
    plt.show()

def show_crossbar(chip,vmin = 0,vmax = 1400,title = "",path = None):
    need_read = np.ones((256,256),dtype=bool)
    # 读器件
    voltage_base = chip.read_point2(crossbar=need_read, read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
    voltage = chip.read_point2(crossbar=need_read, read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
    cond_sub_base = chip.voltage_to_cond(voltage-voltage_base)
    plot_cond(cond_sub_base,vmin,vmax,title,path)

def read_crossbar_sub_base(chip,need_read):
    """
        读矩阵的结果
    """
    voltage_base = chip.read_point2(crossbar=need_read, read_voltage=0,tg=5,gain=1,from_row=True,out_type=0)
    voltage = chip.read_point2(crossbar=need_read, read_voltage=0.1,tg=5,gain=1,from_row=True,out_type=0)
    cond_sub_base = chip.voltage_to_cond(voltage-voltage_base)
    return cond_sub_base