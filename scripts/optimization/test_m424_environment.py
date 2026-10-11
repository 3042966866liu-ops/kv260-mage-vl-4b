"""Real temporary files and symlinks; explicitly fake sysfs, never board proof."""
import tempfile
from pathlib import Path
from m424_environment import temperatures


def main():
    with tempfile.TemporaryDirectory() as name:
        root=Path(name);physical=root/'sys/devices/platform/ams/hwmon/hwmon0'
        physical.mkdir(parents=True)
        driver=root/'sys/bus/platform/drivers/iio_hwmon';driver.mkdir(parents=True)
        device=physical/'device';device.mkdir();(device/'driver').symlink_to(driver,target_is_directory=True)
        node=root/'sys/class/hwmon/hwmon0';node.parent.mkdir(parents=True)
        node.symlink_to(physical,target_is_directory=True)
        (physical/'name').write_text('ams\n')
        for i in (1,2,3):(physical/f'temp{i}_input').write_text(str(31000+i))
        expected=dict(path='/sys/class/hwmon/hwmon0',resolved_path='/sys/devices/platform/ams/hwmon/hwmon0',
                      driver='/sys/bus/platform/drivers/iio_hwmon',name='ams',inputs=['temp1_input','temp2_input','temp3_input'])
        good=temperatures(expected,root);assert len(good)==3 and good['ams/temp1_input']['temperature_mC']==31001
        def refuse(row):
            try:temperatures(row,root)
            except (RuntimeError,ValueError,FileNotFoundError):return
            raise AssertionError('Invalid sysfs identity accepted')
        for k,v in [('resolved_path','/wrong'),('name','ina260'),('driver','/wrong'),('inputs',['temp1_input'])]:
            refuse(dict(expected,**{k:v}))
        for bad in ('NaN','150001','-40001'):
            (physical/'temp1_input').write_text(bad);refuse(expected)
        (physical/'temp1_input').unlink();refuse(expected)
        print('M424_FAKE_SYSFS_COMPONENT_PASS rejects=8')


if __name__=='__main__':main()
