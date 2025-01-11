import matplotlib.pyplot as plt
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