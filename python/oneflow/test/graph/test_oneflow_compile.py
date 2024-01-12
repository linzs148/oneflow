"""
Copyright 2020 The OneFlow Authors. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import unittest

import numpy as np
import oneflow as flow
import oneflow.unittest
import torch
from oneflow.framework import infer_compiler


class TorchModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linears = torch.nn.ModuleList([torch.nn.Linear(10, 10) for i in range(10)])

    def forward(self, x):
        for i, l in enumerate(self.linears):
            x = self.linears[i // 2](x) + l(x)
        return x


class OneflowModule(flow.nn.Module):
    def __init__(self):
        super().__init__()
        self.linears = flow.nn.ModuleList([flow.nn.Linear(10, 10) for i in range(10)])

    def forward(self, x):
        for i, l in enumerate(self.linears):
            x = self.linears[i // 2](x) + l(x)
        return x


@unittest.skipIf(os.getenv("ONEFLOW_TEST_CPU_ONLY"), "only test cpu cases")
@flow.unittest.skip_unless_1n1d()
class TestOneflowCompile(flow.unittest.TestCase):
    def test_oneflow_compile(test_case):
        infer_compiler.register(torch2oflow_class_map={TorchModule: OneflowModule})

        m = TorchModule().to("cuda")
        x = torch.randn(2, 10).to("cuda")
        y_torch = m(x)

        m = infer_compiler.compile_from_torch(m)
        y_oneflow = m(x)

        assert np.allclose(
            y_torch.detach().cpu(), y_oneflow.detach().cpu(), 1e-03, 1e-03
        )

        from oneflow.framework.infer_compiler.with_oneflow_compile import (
            DualModule, DualModuleList)

        assert isinstance(m.linears, DualModuleList)

        x = getattr(m.linears, "1")
        assert isinstance(x, DualModule)

        x.bias = None
        setattr(m.linears, "2", x)

        assert m.linears[2].bias is None
        assert m.linears._torch_modules[2].bias is None
        assert m.linears._oneflow_modules[2].bias is None

        m.linears[3] = x

        assert m.linears[3].bias is None
        assert m.linears._torch_modules[3].bias is None
        assert m.linears._oneflow_modules[3].bias is None


if __name__ == "__main__":
    unittest.main()
