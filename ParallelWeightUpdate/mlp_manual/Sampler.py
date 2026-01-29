import random
import numpy as np
from scipy.stats import qmc

class Sampler:
    """
    统一的随机数采样器,支持三种模式：
        - "random": 均匀随机(Python 内置 random / numpy)
        - "halton": Halton 低差异序列
        - "sobol": Sobol 低差异序列

    参数:
        mode (str): 采样模式,可选 "random", "halton", "sobol"
        d (int): 采样维度,默认为 2(适用于 (a, b) 阈值对)
        scramble (bool): 是否打乱低差异序列(默认 False,保证可复现)
        max_length (int): Halton/Sobol 的最大采样长度,超过则重置(默认 2**16)

    sample 返回 numpy.ndarray, dtype=np.float32, shape (n, d)
    """
    def __init__(
        self,
        mode: str = "random",
        d: int = 2,
        scramble: bool = False,
        sliding: bool = True,
        max_length: int = 2**16
    ):
        self.mode = mode
        self.d = d
        self.scramble = scramble
        self.max_length = max_length
        self.sliding = sliding

        if mode == "halton":
            self.sampler = qmc.Halton(d=d, scramble=scramble)
            self._consumed = 0
            # 跳过第一个点(通常是全0),避免边界问题
            self.sampler.random(1)
            self._consumed += 1
        elif mode == "sobol":
            self.sampler = qmc.Sobol(d=d, scramble=scramble)
            self._consumed = 0
            # Sobol 要求 n 是 2 的幂,但 qmc.Sobol 支持任意 n(内部补零)
            # 同样跳过第一个点
            self.sampler.random(1)
            self._consumed += 1
        elif mode == "random":
            self.sampler = None
            self._consumed = 0
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def sample(self, n: int) -> np.ndarray:
        """
        采样 n 个 d 维的 [0, 1) 区间内的点。

        返回:
            numpy.ndarray of shape (n, d), dtype=np.float32
        """
        if self.mode == "random":
            # 使用 numpy 生成均匀随机数
            samples = np.random.random((n, self.d)).astype(np.float32)
            return samples
        
        elif self.mode in ("halton", "sobol"):
            # 检查是否需要重置
            if self._consumed + n > self.max_length:
                self.reset()

            rd = self.sampler.random(n)
            self._consumed += n

            if self.sliding == False:
                self.reset()
            return rd.astype(np.float32)

        else:
            raise RuntimeError("Unexpected mode")

    def reset(self):
        """手动重置采样器状态(仅对 halton/sobol 有效)"""
        if self.mode in ("halton", "sobol"):
            self.sampler.reset() # type: ignore
            self.sampler.random(1)
            self._consumed = 1

    def __repr__(self):
        return f"Sampler(mode={self.mode}, d={self.d}, consumed={self._consumed})"