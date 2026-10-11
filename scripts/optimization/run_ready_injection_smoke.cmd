@echo off
setlocal
set "ROOT=C:\Users\30429\Desktop\TeLLMe_FPGA_2026"
if exist "%ROOT%\tmp\op01_ready_injection_smoke" exit /b 2
mkdir "%ROOT%\tmp\op01_ready_injection_smoke"
cd /d "%ROOT%\tmp\op01_ready_injection_smoke"
call D:/AMDDesignTools/2026.1/Vivado/bin/xvlog -sv "%ROOT%\hls\mage_decode_op01_one\tb_ready_injection.sv"
if errorlevel 1 exit /b %errorlevel%
call D:/AMDDesignTools/2026.1/Vivado/bin/xelab tb_ready_injection -s ready_smoke
if errorlevel 1 exit /b %errorlevel%
call D:/AMDDesignTools/2026.1/Vivado/bin/xsim ready_smoke -R
exit /b %errorlevel%
