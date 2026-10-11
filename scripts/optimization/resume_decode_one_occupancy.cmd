@echo off
call D:/AMDDesignTools/2026.1/Vivado/bin/xsim -testplusarg "UVM_VERBOSITY=UVM_NONE" -testplusarg "UVM_TESTNAME=op01_decode_one_kernel_test_lib" -testplusarg "UVM_TIMEOUT=20000000000000" --noieeewarnings op01_decode_one_kernel -tclbatch op01_decode_one_kernel.tcl
exit /b %errorlevel%
