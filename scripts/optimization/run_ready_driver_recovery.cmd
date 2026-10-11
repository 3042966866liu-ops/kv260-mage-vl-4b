@echo off
setlocal
set "ROOT=C:\Users\30429\Desktop\TeLLMe_FPGA_2026"
if exist "%ROOT%\tmp\op01_ready_driver_recovery" exit /b 2
mkdir "%ROOT%\tmp\op01_ready_driver_recovery"
cd /d "%ROOT%\tmp\op01_ready_driver_recovery"
call D:/AMDDesignTools/2026.1/Vivado/bin/xvlog -sv "%ROOT%\hls\mage_decode_op01_one\tb_ready_driver_recovery.sv"
if errorlevel 1 exit /b %errorlevel%
call D:/AMDDesignTools/2026.1/Vivado/bin/xelab tb_ready_driver_recovery -s driver_recovery
if errorlevel 1 exit /b %errorlevel%
call D:/AMDDesignTools/2026.1/Vivado/bin/xsim driver_recovery -R
exit /b %errorlevel%
