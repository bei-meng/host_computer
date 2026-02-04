import torch
import torch.nn as nn
import numpy as np
import torch.nn.functional as F
chunk_size = 32


class Module:
    def inference_unsign(self,row_index,col_index,from_row):
        config = self.config
        num = len(row_index) if from_row else len(col_index)
        if num<=0: return 0
        _,c,_ = config.chip.read4(crossbar=None,row_index=row_index,
                col_index=col_index,
                read_voltage=0.1,tg=5,gain=1,sub_base=True,
                from_row=from_row,split_type=4,row_type=0,col_type=0,
                return_data=False,return_base=False)

        if config.cToW_m=="reference":
            return config.cToW*(c-config.ref_c*num)*1e-6
        elif config.cToW_m=="difference":
            return config.cToW*c*1e-6
        return 0
    def forward(self, x):
        raise NotImplementedError

    def backward(self, grad):
        raise NotImplementedError

    def params(self):
        return []

# 每一层的配置信息
class LayerConfig:
    forward = "software"
    chip = None
    from_row = False
    row_index = None
    col_index = None
    quant = "noShift"                                       # 0表示每个切片的权重一样
    bit = 8                                         # 表示切片的数量
    cToW = 0.1                                      # 电导cond到权重的缩放比例
    cToW_m = "reference"                            # 权重映射电导的方式
    ref_c = 550                                     # reference电导值550us


    update = "software"
    lr = 0.01
    BL = 1
    cTop = 1                                        # 电导变化量到脉宽的比例
    wv = 3                                          # 写入电压


    sampler = None                                  # 随机数采样器

    def __init__(self,**kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


#------------------------------------------------------------------------------------------
# ************************************** Linear线性层 **************************************
#------------------------------------------------------------------------------------------


class Linear(Module):
    def __init__(self, in_features, out_features, config, bias=True):
        limit = np.sqrt(6 / (in_features + out_features))
        self.W = np.random.uniform(-limit, limit, (in_features, out_features))
        self.b = np.zeros(out_features) if bias else None

        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b) if bias else None

        self._x = None

        self.config:LayerConfig = config
    
    def hardware_forward(self, x, from_row, save_x=True):
        row_index,col_index = self.config.row_index,self.config.col_index
        bits = self.config.bit

        if self.config.quant == "noShift":
            x_scale = np.max(np.abs(x)) / bits
            self._x = np.floor(x / x_scale) * x_scale if save_x else None

            batch_size,output_size = x.shape[0],self.W.shape[1]
            all_outputs = np.zeros((batch_size,output_size))
            # 一个batch多张图片
            for k in range(batch_size):
                out = np.zeros((self.config.chip.setting.chip_latch_num))
                for i in range(bits):
                    if from_row:
                        # 正数
                        index = row_index[np.where(x[k] >= x_scale * (i + 1))]
                        out += self.inference_unsign(row_index=index, col_index=col_index, from_row=from_row)
                        # 负数
                        index = row_index[np.where(x[k] <= -x_scale * (i + 1))]
                        out -= self.inference_unsign(row_index=index, col_index=col_index, from_row=from_row)
                    else:
                        # 正数
                        index = col_index[np.where(x[k] >= x_scale * (i + 1))]
                        out += self.inference_unsign(row_index=row_index, col_index=index, from_row=from_row)
                        # 负数
                        index = col_index[np.where(x[k] <= -x_scale * (i + 1))]
                        out -= self.inference_unsign(row_index=row_index, col_index=index, from_row=from_row)

                result_single = (out[col_index] if from_row else out[row_index]) * x_scale

                all_outputs[k,:] = result_single
            return all_outputs

    def software_forward(self,x,save_x=True):
        self._x = np.ascontiguousarray(x) if save_x else None
        out = self._x.dot(self.W)
        if self.b is not None:
            out = out + self.b
        return out
    
    def forward(self, x):
        if self.config.forward == "software":
            return self.software_backward(x, save_x = True)
        elif self.config.forward == "hardware":
            return self.hardware_forward(x, from_row = self.config.from_row, save_x = True)


    def hardware_update(self,row_index,col_index,pulse_width,set_device):
        """
            这里不明确
        """
        if len(row_index)==0 or len(col_index)==0:
            return
        self.config.chip.write4(crossbar=None,row_index=row_index,
                    col_index=col_index,
                    write_voltage=self.config.wv,tg=5,pulse_width=pulse_width,
                    set_device=set_device,
                    split_type=5,row_type=int(not set_device),col_type=0)

    def hardware_backward(self, grad):
        grad_input = self.hardware_forward(grad,from_row=not self.config.from_row,save_x=False)
        row_index,col_index = self.config.row_index,self.config.col_index

        BL = self.config.BL
        x,y = self._x, grad
        inputScale,outputScale = np.max(np.abs(x)), np.max(np.abs(y))
        rd = self.sampler.sample(BL)  # (BL, 2)
        x_random,y_random = rd[:, 0] * inputScale,rd[:, 1] * outputScale
        pulse_width = (self.config.lr * inputScale * outputScale * self.config.cTop / self.config.cToW) /BL

        # 一个batch多张图片
        for k in range(x.shape[0]):
            for i in range(BL):
                # 都是正的
                self.hardware_update(row_index[x[k] >= x_random[i]],col_index[y[k] >= y_random[i]],pulse_width,set_device=True)
                # x正y负
                self.hardware_update(row_index[x[k] <= -x_random[i]],col_index[y[k] <= -y_random[i]],pulse_width,set_device=False)
                # x负y正
                self.hardware_update(row_index[x[k] >= x_random[i]],col_index[y[k] <= -y_random[i]],pulse_width,set_device=False)
                # 都是负的
                self.hardware_update(row_index[x[k] <= -x_random[i]],col_index[y[k] >= y_random[i]],pulse_width,set_device=True)
        return grad_input
    
    def software_backward(self, grad):
        grad_input = grad.dot(self.W.T)

        BL = self.config["BL"]
        out_features = grad.shape[1]
        in_features = self._x.shape[1]

        if BL == 0:
            self.dW = self._x.T.dot(grad)
        else:
            x,y = self._x, grad
            inputScale,outputScale = np.max(np.abs(x)), np.max(np.abs(y))
            rd = self.sampler.sample(BL)  # (BL, 2)

            grad_weight_acc = np.zeros((out_features, in_features))

            for i in range(0, BL, chunk_size):
                end = min(i + chunk_size, BL)
                rd_chunk = rd[i:end]  # (n, 2)
                x_random,y_random = rd_chunk[:, 0] * inputScale,rd_chunk[:, 1] * outputScale  # (n,),(n,)
                x_random, y_random = x_random[:, None, None], y_random[:, None, None] # 扩展用于广播: (n, 1, 1)
                x_exp, y_exp = x[None, :, :], y[None, :, :] # (B, out) -> (1, B, out)
                tmpx = (x_exp >= x_random).astype(np.int32) - (x_exp <= -x_random).astype(np.int32)
                tmpy = (y_exp >= y_random).astype(np.int32) - (y_exp <= -y_random).astype(np.int32)
                grad_weight_acc += np.einsum('nbo,nbi->oi', tmpy, tmpx) # (n, B, in),(n, B, out),

            self.dW = (grad_weight_acc.T * (outputScale * inputScale / BL))

        if self.b is not None:
            self.db = grad.sum(axis=0)
        
        lr = float(self.config['lr'])
        for p, g in self.params():
            if g is None:
                continue
            p[...] -= lr * g

        return grad_input
    
    def backward(self, grad):        
        if self.config.update == "software":
            return self.software_backward(grad)
        elif self.config.update == "hardware":
            return self.hardware_backward(grad)

    def params(self):
        if self.b is not None:
            return [(self.W, self.dW), (self.b, self.db)]
        return [(self.W, self.dW)]



class Conv2d(Module):
    def __init__(self, in_channels, out_channels, kernel_size, config, stride=1, padding=0, dilation=1, bias=True):
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.kernel_size = (kernel_size, kernel_size) if isinstance(kernel_size, int) else kernel_size
        self.stride = (stride, stride) if isinstance(stride, int) else stride
        self.padding = (padding, padding) if isinstance(padding, int) else padding
        self.dilation = (dilation, dilation) if isinstance(dilation, int) else dilation
        self.bias = bias
        self.config = config

        # Xavier 初始化
        kh, kw = self.kernel_size
        limit = np.sqrt(6 / (in_channels * kh * kw + out_channels * kh * kw))
        self.W = np.random.uniform(-limit, limit, (out_channels, in_channels, kh, kw))
        self.b = np.zeros(out_channels) if bias else None

        # 梯度缓存
        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b) if bias else None

        # 用于反向传播的输入缓存
        self._x = None  # 展开后的输入
        self._x_shape_origin = None # 原始输入形状

    def software_forward(self, input, save_x=True):
        # 维度为(B, C_in, H_in, W_in)
        batch, _, input_h, input_w = input.shape
        # 维度为(C_out, C_in, K_h, K_w)
        out_channels, _, kernel_h, kernel_w = self.W.shape

        padding, dilation, stride = self.padding,self.dilation,self.stride
        # 计算输出尺寸（注意：此实现暂不支持 groups != 1）
        output_h = (input_h + 2 * padding[0] - dilation[0] * (kernel_h - 1) - 1) // stride[0] + 1
        output_w = (input_w + 2 * padding[1] - dilation[1] * (kernel_w - 1) - 1) // stride[1] + 1

        # 展开输入: (B, K(C_in * K_h * K_w), L(滑动窗口数量)) → 转置为 (B, L, K)
        region_matrix = F.unfold(torch.from_numpy(input), (kernel_h, kernel_w), dilation=dilation, padding=padding, stride=stride).transpose(1, 2)

        # 权重: (out_channels, K) --> (K, C_out)
        kernel_matrix = torch.from_numpy(self.W.view(out_channels, -1).t())

        # 输出
        output_matrix = torch.matmul(region_matrix, kernel_matrix)  # (B, L, C_out)

        if self.bias:
            output_matrix += self.b  # (C_out,) 自动广播到 (B, L, C_out)

        output = output_matrix.transpose(1, 2).view(batch, out_channels, output_h, output_w)

        if save_x:
            self._x = region_matrix.numpy()
            self._x_shape_origin = input.shape

        # (batch, out_channels, output_h, output_w)
        return output.numpy()

    def hardware_forward(self, input, from_row, save_x=True):
        # 维度为(B, C_in, H_in, W_in)
        batch, _, input_h, input_w = input.shape
        # 维度为(C_out, C_in, K_h, K_w)
        out_channels, _, kernel_h, kernel_w = self.W.shape

        padding, dilation, stride = self.padding,self.dilation,self.stride
        # 计算输出尺寸（注意：此实现暂不支持 groups != 1）
        output_h = (input_h + 2 * padding[0] - dilation[0] * (kernel_h - 1) - 1) // stride[0] + 1
        output_w = (input_w + 2 * padding[1] - dilation[1] * (kernel_w - 1) - 1) // stride[1] + 1

        # 展开输入: (B, K(C_in * K_h * K_w), L(滑动窗口数量)) → 转置为 (B, L, K)
        region_matrix = F.unfold(torch.from_numpy(input), (kernel_h, kernel_w), dilation=dilation, padding=padding, stride=stride).transpose(1, 2).numpy()

        row_index,col_index = self.config.row_index,self.config.col_index
        bits = self.config.bit

        if self.config.quant == "noShift":
            x_scale = np.max(np.abs(region_matrix)) / bits
            if save_x:
                self._x = np.floor(region_matrix / x_scale) * x_scale if save_x else None
                self._x_shape_origin = input.shape
            
            # (B, L, C_out)
            all_outputs = np.zeros((batch,region_matrix.shape[1],out_channels))
            # 一个batch多张图片
            for k in range(region_matrix.shape[0]):
                # 切分为L次推理，每次推理切分为8bit
                for L in range(region_matrix.shape[1]):
                    out = np.zeros((self.config.chip.setting.chip_latch_num))
                    for i in range(bits):
                        if from_row:
                            # 正数
                            index = row_index[np.where(region_matrix[k,L] >= x_scale * (i + 1))]
                            out += self.inference_unsign(row_index=index, col_index=col_index, from_row=from_row)
                            # 负数
                            index = row_index[np.where(region_matrix[k,L] <= -x_scale * (i + 1))]
                            out -= self.inference_unsign(row_index=index, col_index=col_index, from_row=from_row)
                        else:
                            # 正数
                            index = col_index[np.where(region_matrix[k,L] >= x_scale * (i + 1))]
                            out += self.inference_unsign(row_index=row_index, col_index=index, from_row=from_row)
                            # 负数
                            index = col_index[np.where(region_matrix[k,L] <= -x_scale * (i + 1))]
                            out -= self.inference_unsign(row_index=row_index, col_index=index, from_row=from_row)

                    result_single = (out[col_index] if from_row else out[row_index]) * x_scale

                    all_outputs[k,L,:] = result_single

            if self.bias:
                all_outputs += self.b  # (C_out,) 自动广播到 (B, L, C_out)

            output = all_outputs.transpose(1, 2).view(batch, out_channels, output_h, output_w)
            return output

    def forward(self, x):
        if self.config.forward == "software":
            return self.software_forward(x, save_x=True)
        elif self.config.forward == "hardware":
            return self.hardware_forward(x, from_row=self.config.from_row, save_x=True)

    def software_backward(self, grad):
        batch, in_channels, input_h, input_w = self._x_shape_origin
        out_channels, in_channels, kernel_h, kernel_w = self.W.shape
        padding, dilation, stride = self.padding,self.dilation,self.stride

        grad_output_flat = grad.view(batch, out_channels, -1)  # (B, C_out, L)

        grad_input = grad_weight = grad_bias = None

        go_t = grad_output_flat.transpose(1, 2)  # (B, L, C_out)
        kernel_mat = self.W.view(out_channels, -1)  # (C_out, K)
        grad_region = torch.matmul(go_t, kernel_mat)  # (B, L, K)
        grad_region = grad_region.transpose(1, 2)  # (B, K, L)
        grad_input = F.fold(grad_region, output_size=(input_h, input_w), kernel_size=(kernel_h, kernel_w), dilation=dilation, padding=padding, stride=stride)

        BL = self.config["BL"]
        B, C_out, L = grad_output_flat.shape
        K = self._x.shape[2]
        region_matrix = self._x

        if BL == 0:
            grad_weight = torch.sum(torch.matmul(grad_output_flat, region_matrix), dim=0)  # (C_out, K)
            grad_weight = grad_weight.view(self.W.shape)
        else:
            # (B, L, K) # (B, C_out, L)
            x,y = region_matrix, grad_output_flat
            inputScale,outputScale = np.max(np.abs(x)), np.max(np.abs(y))
            rd = self.sampler.sample(BL)  # (BL, 2)

            grad_weight_acc = torch.zeros(C_out, K)

            for i in range(0, BL, chunk_size):
                end = min(i + chunk_size, BL)
                a_vals = rd[i:end, 0] * outputScale
                b_vals = rd[i:end, 1] * inputScale

                a_exp = a_vals[:, None, None, None]  # (n, 1, 1, 1)
                b_exp = b_vals[:, None, None, None]  # (n, 1, 1, 1)

                # (B, C_out, L) → (1, B, C_out, L)
                y_exp = y[None, :, :, :]  # (1, B, C_out, L)
                x_exp = x[None, :, :, :]  # (1, B, L, K)

                # tmpy = +1 if y >= a, -1 if y <= -a, else 0
                tmpy = (y_exp >= a_exp).astype(np.float32) - (y_exp <= -a_exp).astype(np.float32)  # (n, B, C_out, L)
                tmpx = (x_exp >= b_exp).astype(np.float32) - (x_exp <= -b_exp).astype(np.float32)  # (n, B, L, K)

                # 累加：einsum 是最优的
                grad_weight_acc += torch.einsum('nbcl,nblk->ck', tmpy, tmpx)

            scale = outputScale * inputScale / BL
            grad_weight = (grad_weight_acc * scale)
            grad_weight = grad_weight.view(self.W.shape)

        self.dW = (grad_weight.T * (outputScale * inputScale / BL))

        if self.b is not None:
            self.db = grad_output_flat.sum(dim=(0, 2))  # (C_out,)
        
        lr = float(self.config['lr'])
        for p, g in self.params():
            if g is None:
                continue
            p[...] -= lr * g

        return grad_input

    def hardware_backward(self, grad):
        # 硬件反向传播逻辑 (简化版)
        # 实际逻辑取决于你的存内计算架构
        grad_input = self.hardware_forward(grad, from_row=not self.config.from_row, save_x=False)
        
        # 这里省略具体的硬件写入逻辑，与 Linear 类类似
        # 需要根据 _x_col 和 grad 计算脉冲
        return grad_input

    def backward(self, grad):
        if self.config.update == "software":
            return self.software_backward(grad)
        elif self.config.update == "hardware":
            return self.hardware_backward(grad)

    def params(self):
        if self.b is not None:
            return [(self.W, self.dW), (self.b, self.db)]
        return [(self.W, self.dW)]

#------------------------------------------------------------------------------------------
# ************************************** 神经网络模块 **************************************
#------------------------------------------------------------------------------------------

class ReLU(Module):
    def __init__(self):
        self._mask = None

    def forward(self, x):
        self._mask = x > 0
        return x * self._mask

    def backward(self, grad):
        return grad * self._mask


class Sigmoid(Module):
    def __init__(self):
        self._out = None

    def forward(self, x):
        out = 1 / (1 + np.exp(-x))
        self._out = out
        return out

    def backward(self, grad):
        return grad * (self._out * (1 - self._out))


def softmax(logits):
    # logits: (batch, classes)
    z = logits - np.max(logits, axis=1, keepdims=True)
    exp = np.exp(z)
    return exp / np.sum(exp, axis=1, keepdims=True)


class Flatten(Module):
    def __init__(self):
        self._input_shape = None

    def forward(self, x):
        """
        将输入 x 从 (B, C, H, W) 或 (B, ...) 展平为 (B, C*H*W)
        """
        self._input_shape = x.shape
        out = x.reshape(x.shape[0], -1)
        return out

    def backward(self, grad):
        """
        将梯度 grad 从 (B, C*H*W) 恢复为前向传播前的形状 (B, C, H, W)
        """
        return grad.reshape(self._input_shape)

class SoftmaxCrossEntropy:
    def __init__(self):
        self.probs = None
        self.labels = None

    def forward(self, logits, labels):
        probs = softmax(logits)
        self.probs = probs
        self.labels = labels

        batch = logits.shape[0]
        log_likelihood = -np.log(probs[np.arange(batch), labels] + 1e-12)
        loss = log_likelihood.mean()

        preds = np.argmax(probs, axis=1) 
        correct_count = (preds == labels).sum()

        return loss, correct_count

    def backward(self):
        probs = self.probs.copy()
        batch = probs.shape[0]
        probs[np.arange(batch), self.labels] -= 1
        probs /= batch
        return probs


class Network(Module):
    def __init__(self):
        self.layers = []

    def append(self,layer):
        self.layers.append(layer)

    def forward(self, x):
        out = x
        for layer in self.layers:
            out = layer.forward(out)
        return out

    def backward(self, grad):
        out = grad
        for layer in reversed(self.layers):
            out = layer.backward(out)

        return out
