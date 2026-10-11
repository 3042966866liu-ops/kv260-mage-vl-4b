"""Actual reader over own files; reject any path outside clocks/storage."""
import tempfile
from pathlib import Path
import m425_environment as env
def main():
    realpath=env.Path;requested=[]
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);cpu=root/'sys/devices/system/cpu/cpufreq/policy0';cpu.mkdir(parents=True)
        for key,value in zip(env.CPU_FIELDS,['cpufreq-dt','userspace','333333','1333333','0 1 2 3','1333333']):(cpu/key).write_text(value)
        clk=root/'sys/kernel/debug/clk/clk_summary';clk.parent.mkdir(parents=True);clk.write_text(' clock enable prepare rate\n pl0_ref 1 1 99999999\n pl1_ref 1 1 99999999\n')
        mount=root/'proc/self/mountinfo';mount.parent.mkdir(parents=True);mount.write_text('explicitly fake mountinfo')
        weights=root/'home/ubuntu/tellme_release_install_20260926';weights.mkdir(parents=True)
        allowed={'/sys/devices/system/cpu/cpufreq','/sys/kernel/debug/clk/clk_summary','/proc/self/mountinfo','/home/ubuntu/tellme_release_install_20260926'}
        def path(name):
            requested.append(name)
            if name not in allowed:raise AssertionError('Unauthorized observer path: '+name)
            return root/name.lstrip('/')
        env.Path=path
        try:
            good=env.read_environment();assert not good['observability_issues'] and good['temperature_measurement_enabled'] is False
            clk.unlink();assert env.read_environment()['observability_issues']
        finally:env.Path=realpath
    assert set(requested)<=allowed
    print('M425_NO_TEMPERATURE_READER_COMPONENT_PASS')
if __name__=='__main__':main()
