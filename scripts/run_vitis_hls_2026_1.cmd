@echo off
setlocal
REM This workstation's AMD 2026.1 installation is on D:, not C:.
REM Do not call the vendor settings64.bat: it hard-codes the invalid C: path.
set "TELLME_VITIS_ROOT=D:\AMDDesignTools\2026.1\Vitis"
set "TELLME_VIVADO_ROOT=D:\AMDDesignTools\2026.1\Vivado"
set "XILINX_VITIS=%TELLME_VITIS_ROOT%"
set "XILINX_HLS=%TELLME_VITIS_ROOT%"
set "XILINX_VIVADO=%TELLME_VIVADO_ROOT%"
set "RDI_PLATFORM=win64"
set "PATH=%TELLME_VITIS_ROOT%\bin;%TELLME_VIVADO_ROOT%\bin;%TELLME_VIVADO_ROOT%\lib\win64.o;%PATH%"
call "%TELLME_VITIS_ROOT%\bin\vitis-run.bat" %*
exit /b %ERRORLEVEL%
