# 当前源码的运行约束

本次GitHub整理不访问COM3、不加载Overlay、不重新训练或测速，也不改变正在运行的网页或板端进程。

上板顺序固定为Build-ID→单descriptor→单chain→单layer→固定文本E2E→任意输入/Web。任一层失败只在该层排查；保留原返回码和日志，不重跑完整模型来修报告。

控制与授权使用COM3；不使用SSH。Ethernet只用于特定peer的有界哈希校验传输，并恢复临时地址；不得修改原路由、boot、DTB、CMA或稳定回滚。Overlay前须在同一终端确认root、XILINX_XRT=/usr、TMPDIR=/dev/shm、PYNQ-venv的xclbinutil优先、xclProbe()==1、单一PYNQ设备和清单SHA。不用/usr/bin/xclbinutil。

存在未知或失败保留进程时，不自动发信号、free、reset或重载Overlay。07工作器拥有七个缓冲区和COM3时，不能启动第二个桥或串口终端；按正常停止协议完成七owner逆序释放及稳定Overlay/四时钟恢复，再声称退出闭合。

发布配置包含历史boot与SHA，只提供源码身份，不把它当成另一台机器或重启后可沿用的授权。历史故障恢复脚本不是普通启动流程。

Windows本项目原环境无裸python命令，原源码显式使用固定Python与PowerShell路径。WSL应指定Ubuntu-24.04及绝对venv。移植环境应新建版本化合同并按门禁验证，不能静默移除身份/数值/权限检查。
