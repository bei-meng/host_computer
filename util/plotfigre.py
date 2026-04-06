import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import numpy as np

def plot_images_list(data_list, pos=None, title_list=None, vmin=None,
                     cmap=plt.cm.viridis, cbar_label="Value", save_path=None):
    """
    自动根据数据数量绘制子图：一行最多3张，自动换行
    :param data_list: 数据列表 [data1, data2, data3, ...]
    :param pos: 灰色窗口坐标 (x1, y1, x2, y2)
    :param title_list: 标题列表
    :param vmin: 全局统一最小值
    :param cmap: 配色
    :param cbar_label: 色条标签
    :param save_path: 保存路径
    """
    n = len(data_list)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    if n == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    text_style = {'color':'k', 'fontsize':10, 'bbox':dict(facecolor='w', alpha=0.7)}

    for i in range(n):
        data = data_list[i]
        ax = axes[i]
        vmin_use = vmin if vmin is not None else np.nanmin(data)
        vmax_use = np.nanmax(data)
        norm = Normalize(vmin=vmin_use, vmax=vmax_use)
        im = ax.imshow(data, cmap=cmap, norm=norm)

        if title_list and i < len(title_list):
            ax.set_title(title_list[i], fontsize=11)

        roi_data = data[pos] if pos is not None else data
        mean_val = np.nanmean(roi_data)
        std_val = np.nanstd(roi_data)

        ax.text(0.98, 0.98, f'mean={mean_val:.3f}\nstd={np.std(std_val):.3f}', ha='right', va='top', transform=ax.transAxes, **text_style)
        fig.colorbar(im, ax=ax, label=cbar_label)

    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.show()

def plot_v(v,figsize=(12,4),title=""):
    """
        绘制电压电导曲线图
    """
    plt.figure(figsize=figsize)
    plt.title = title

    # plt.subplot(1,2,1)
    plt.plot(v,marker='o', linestyle='-', linewidth=2,label="voltage")
    plt.ylabel("voltage(v)")
    plt.xlabel("TIA")
    plt.legend()

    # plt.subplot(1,2,2)
    # plt.plot(cond,marker='o', linestyle='-', linewidth=2,label="cond")
    # plt.ylabel("cond(us)")
    # plt.xlabel("TIA")

    # plt.legend()
    plt.show()


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


def plot_hist(data,bin_min=0,bin_max=1000,interval=5):
    bin_edges = np.linspace(bin_min, bin_max, int(bin_max/interval)+1)  
    data = data.flatten()
    counts, bin_edges, _ = plt.hist(data, bins=bin_edges, color='blue', alpha=0.7, edgecolor='None')
    plt.xlabel("us")
    plt.ylabel("frequency")
    plt.title("hist")
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