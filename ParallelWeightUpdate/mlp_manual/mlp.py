import numpy as np
chunk_size = 32


class Module:
    def forward(self, x):
        raise NotImplementedError

    def backward(self, grad):
        raise NotImplementedError

    def params(self):
        return []


class Linear(Module):
    def __init__(self, in_features, out_features, sampler,layer_info, bias=True):
        limit = np.sqrt(6 / (in_features + out_features))
        self.W = np.random.uniform(-limit, limit, (in_features, out_features))
        self.b = np.zeros(out_features) if bias else None

        self.dW = np.zeros_like(self.W)
        self.db = np.zeros_like(self.b) if bias else None

        self._x = None

        self.sampler = sampler
        self.layer_info = layer_info


    def inference(self,chip,row_index,col_index,from_row,layer_info):
        """
            调用硬件接口真正实现推理计算
            仅能实现01输入的计算
        """
        num = len(row_index) if from_row else len(col_index)
        if num>0:
            _,c,_ = chip.read4(crossbar=None,row_index=row_index,
                    col_index=col_index,
                    read_voltage=0.1,tg=5,gain=1,sub_base=True,
                    from_row=from_row,split_type=4,row_type=0,col_type=0,
                    return_data=False,return_base=False)

            if layer_info["cond_to_weight_method"]=="reference":
                return layer_info["cond_to_weight_scale"]*(c-layer_info["reference_cond"]*num)*1e-6
            elif layer_info["cond_to_weight_method"]=="difference":
                return layer_info["cond_to_weight_scale"]*c*1e-6
        return 0
    
    def hardware_forward(self, x, from_row, save_x=True):
        chip = self.layer_info["chip"]
        row_index = self.layer_info["row_index"]
        col_index = self.layer_info["col_index"]
        bits = self.layer_info["quantization_bits"]


        x_scale = np.max(np.abs(x)) / bits
        if save_x:
            self._x = np.floor(x / x_scale) * x_scale

        if self.layer_info["quantization"] == "noShift":
            all_outputs = []
            # 一个batch多张图片
            for i in range(x.shape[0]):
                out = np.zeros((chip.setting.chip_latch_num))
                for i in range(bits):
                    if from_row:
                        # 正数
                        index = row_index[np.where(x[i] >= x_scale * (i + 1))]
                        out += self.inference(chip, row_index=index, col_index=col_index,
                                    from_row=from_row, layer_info=self.layer_info)
                        # 负数
                        index = row_index[np.where(x[i] <= -x_scale * (i + 1))]
                        out -= self.inference(chip, row_index=index, col_index=col_index,
                                    from_row=from_row, layer_info=self.layer_info)
                    else:
                        # 正数
                        index = col_index[np.where(x[i] >= x_scale * (i + 1))]
                        out += self.inference(chip, row_index=row_index, col_index=index,
                                    from_row=from_row, layer_info=self.layer_info)
                        # 负数
                        index = col_index[np.where(x[i] <= -x_scale * (i + 1))]
                        out -= self.inference(chip, row_index=row_index, col_index=index,
                                    from_row=from_row, layer_info=self.layer_info)

                # 处理当前样本的输出
                if from_row:
                    result_single = out[col_index] * x_scale
                else:
                    result_single = out[row_index] * x_scale

                all_outputs.append(result_single)

            # batch处理结果的聚合
            return np.stack(all_outputs)

    def forward(self, x):
        # 前向函数，调用软件实现或硬件实现的
        if self.layer_info["forward"]=="software":
            self._x = np.ascontiguousarray(x)
            out = self._x.dot(self.W)
            if self.b is not None:
                out = out + self.b
            return out
        elif self.layer_info["forward"]=="hardware":
            return self.hardware_forward(x,from_row=self.layer_info["from_row"],save_x=True)

    def software_backward(self, grad):
        grad_input = grad.dot(self.W.T)


        BL = self.layer_info["BL"]
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
        

        lr = float(self.layer_info['lr'])
        for p, g in self.params():
            if g is None:
                continue
            p[...] -= lr * g

        return grad_input
    

    def hardware_update(self,chip,row_index,col_index,write_voltage,pulse_width,set_device):
        """
            这里不明确
        """
        if len(row_index)==0 or len(col_index)==0:
            return
        chip.write4(crossbar=None,row_index=row_index,
                    col_index=col_index,
                    write_voltage=write_voltage,tg=5,pulse_width=pulse_width,
                    set_device=set_device,
                    split_type=5,row_type=int(not set_device),col_type=0)

    def hardware_backward(self, grad):
        # 转置计算
        grad_input = self.hardware_forward(grad,from_row=not self.layer_info["from_row"],save_x=False)
        
        chip = self.layer_info["chip"]
        row_index = self.layer_info["row_index"]
        col_index = self.layer_info["col_index"]

        BL = self.layer_info["BL"]
        x,y = self._x, grad
        inputScale,outputScale = np.max(np.abs(x)), np.max(np.abs(y))
        rd = self.sampler.sample(BL)  # (BL, 2)
        x_random,y_random = rd[:, 0] * inputScale,rd[:, 1] * outputScale
        pulse_width = self.layer_info["lr"]*inputScale*outputScale*self.layer_info["cond_to_pulse_width"]/self.layer_info["cond_to_weight_scale"]/BL
        write_voltage = self.layer_info["write_voltage"]

        # 一个batch多张图片
        for k in range(x.shape[0]):
            for i in range(BL):
                # 都是正的
                self.hardware_update(chip,row_index[x[k] >= x_random[i]],col_index[y[k] >= y_random[i]],write_voltage,pulse_width,set_device=True)
                # x正y负
                self.hardware_update(chip,row_index[x[k] <= -x_random[i]],col_index[y[k] <= -y_random[i]],write_voltage,pulse_width,set_device=True)
                # x负y正
                self.hardware_update(chip,row_index[x[k] >= x_random[i]],col_index[y[k] <= -y_random[i]],write_voltage,pulse_width,set_device=True)
                # 都是负的
                self.hardware_update(chip,row_index[x[k] <= -x_random[i]],col_index[y[k] >= y_random[i]],write_voltage,pulse_width,set_device=True)
        return grad_input
    
    def backward(self, grad):
        if self._x is None:
            raise RuntimeError("Linear.backward called before forward")
        
        if self.layer_info["update"]=="software":
            return self.software_backward(grad)
        elif self.layer_info["update"]=="hardware":
            return self.hardware_backward(grad)

    def params(self):
        if self.b is not None:
            return [(self.W, self.dW), (self.b, self.db)]
        return [(self.W, self.dW)]


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


class SoftmaxCrossEntropy:
    def __init__(self):
        self.probs = None
        self.labels = None

    def forward(self, logits, labels):
        # labels: int class indices, shape (batch,)
        probs = softmax(logits)
        self.probs = probs
        self.labels = labels
        batch = logits.shape[0]
        log_likelihood = -np.log(probs[np.arange(batch), labels] + 1e-12)
        return log_likelihood.mean()

    def backward(self):
        probs = self.probs.copy()
        batch = probs.shape[0]
        probs[np.arange(batch), self.labels] -= 1
        probs /= batch
        return probs


class MLP(Module):
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
            if isinstance(layer, Linear):
                out = layer.backward(out)
            else:
                out = layer.backward(out)
        return out
