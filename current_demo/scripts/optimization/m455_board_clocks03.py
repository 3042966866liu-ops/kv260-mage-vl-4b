"""Bounded PL-only divider control; preserve PLLs and original clock identity."""
import math

TARGET = (187.5, 100.0)


class ClockGuard:
    def __init__(self, clocks):
        self.clocks = clocks
        self.instance = clocks._instance
        self.regs = self.instance.PL_CLK_CTRLS
        self.original = [int(r) for r in self.regs]
        self.divisors = [(int(r.DIVISOR0), int(r.DIVISOR1)) for r in self.regs]
        self.plls = self.pll_identity()
        self.unused = [int(r) for r in self.regs[2:]]
        self.changed = False
        self.events = []
        if any(int(r.SRCSEL) != 0 for r in self.regs[:2]):
            raise RuntimeError('Only original IOPLL sources admitted')

    def pll_identity(self):
        a = self.instance
        return [int(a._crl_registers.IOPLL_CTRL), int(a._crl_registers.RPLL_CTRL),
                int(a._crf_registers.DPLL_CTRL), int(a._crf_registers.APLL_CTRL)]

    def snapshot(self):
        return dict(raw=[int(r) for r in self.regs],
                    mhz={str(i):float(getattr(self.clocks, f'fclk{i}_mhz')) for i in range(4)},
                    pll_raw=self.pll_identity())

    def normalize(self):
        overlay_before = self.snapshot()
        if overlay_before['pll_raw'] != self.plls:
            raise RuntimeError('PLL identity changed during Overlay')
        divider_mask = (63 << 8) | (63 << 16)
        repairs = []
        for index in (2,3):
            current = overlay_before['raw'][index]
            original = self.original[index]
            if (current ^ original) & ~divider_mask:
                raise RuntimeError('Unused PL non-divider identity changed')
            if current != original:
                self.changed = True
                div0,div1 = self.divisors[index]
                self.clocks.set_pl_clk(index,div0=div0,div1=div1)
                repairs.append(dict(index=index,before_raw=current,restored_raw=int(self.regs[index])))
        before = self.snapshot()
        if before['pll_raw'] != self.plls or before['raw'][2:] != self.unused:
            raise RuntimeError('PLL or unused clocks changed')
        # Mark before writing: any exception requires safe cleanup or retention.
        self.changed = True
        self.clocks.set_pl_clk(0, clk_mhz=TARGET[0])
        self.clocks.set_pl_clk(1, clk_mhz=TARGET[1])
        after = self.snapshot()
        validate_operating(after)
        if after['pll_raw'] != self.plls or after['raw'][2:] != self.unused:
            raise RuntimeError('Clock setter changed PLL/unused clock identity')
        self.events.append(dict(before=before, after=after, overlay_before=overlay_before, unused_original_divider_restorations=repairs))
        return after

    def restore(self):
        for i, (div0, div1) in enumerate(self.divisors):
            self.clocks.set_pl_clk(i, div0=div0, div1=div1)
        after = self.snapshot()
        if after['raw'] != self.original or after['pll_raw'] != self.plls:
            raise RuntimeError('Original clock register identity not restored')
        self.changed = False
        return after


def validate_operating(snapshot):
    for index, target in enumerate(TARGET):
        value = snapshot['mhz'][str(index)]
        if not math.isfinite(value) or not target * 0.999 <= value <= target:
            raise RuntimeError('Operating clock outside frozen bounded rate')
    return True
