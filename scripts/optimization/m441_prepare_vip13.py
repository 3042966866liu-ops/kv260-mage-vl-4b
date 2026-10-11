from m351_workflow import HERE,atomic
s=(HERE/'m441_vip_tail_component12.py').read_text(encoding='utf-8-sig')
for a,b in [('component12','component13'),('component_12','component_13'),('component-12','component-13'),('组件12','组件13')]:s=s.replace(a,b)
old='driver.get_and_drive(item);accepted++;';assert s.count(old)==1
s=s.replace(old,'@(negedge rx_clk);driver.get_and_drive(item);accepted++;')
old='$fatal(1,"actual receiver component budget");';assert s.count(old)==1
s=s.replace(old,'$display("VIP_BUDGET words=%0d ready=%0d armed=%0d released=%0d held=%0d accepted=%0d",words,sink.ready,tail_armed,tail_released,tail_hold_valid_cycles,accepted);'+old)
compile(s,'vip13','exec');atomic(HERE/'m441_vip_tail_component13.py',s.encode('utf-8'),immutable=True)
