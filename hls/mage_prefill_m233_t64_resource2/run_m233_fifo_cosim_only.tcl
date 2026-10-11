set project "D:/CodexHome/visualizations/2026/09/01/01a05cf2-5674-7841-b1b8-a9e9eec650fb/m233_t64_fifo_cosim"
open_project $project
open_solution solution1
cosim_design -rtl verilog -random_stall -trace_level none
exit
