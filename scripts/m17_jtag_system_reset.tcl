connect -url TCP:127.0.0.1:3121
targets -set -filter {name =~ "PSU"}
rst -system
after 1000
disconnect
exit
