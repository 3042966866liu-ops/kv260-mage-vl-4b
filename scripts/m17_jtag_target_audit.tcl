connect -url TCP:127.0.0.1:3121
targets -set -filter {name =~ "PSU"}
puts "TELLME_JTAG_PSU_TARGET_SELECTED"
puts [targets]
disconnect
exit
