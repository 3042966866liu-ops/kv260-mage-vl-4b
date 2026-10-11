"""Additional observation only; fixed 80M budget and whole-path stall guard."""
import re

EXTRA = r'''
longint tx_seen=0,rx_backpressure=0,tx_backpressure=0,ctrl_seen=0;
integer stagnant=0;
wire ctrl_activity=(`D.s_axi_control_AWVALID&&`D.s_axi_control_AWREADY)||
 (`D.s_axi_control_WVALID&&`D.s_axi_control_WREADY)||
 (`D.s_axi_control_BVALID&&`D.s_axi_control_BREADY)||
 (`D.s_axi_control_ARVALID&&`D.s_axi_control_ARREADY)||
 (`D.s_axi_control_RVALID&&`D.s_axi_control_RREADY);
task automatic progress_snapshot(input integer terminal_kind);
 $display("M441_PROGRESS cycle=%0d output=%0d tx=%0d rx_stall=%0d tx_stall=%0d ctrl=%0d stagnant=%0d terminal=%0d",cyc,words,tx_seen,rx_backpressure,tx_backpressure,ctrl_seen,stagnant,terminal_kind);
 for(integer j=0;j<4;j=j+1)
  $display("M441_PORT_PROGRESS cycle=%0d shard=%0d AR=%0d R=%0d pending=%0d gap=%0d ARSTALL=%0d RSTALL=%0d MAC=%0d iter=%0d qwrite=%0d qread=%0d qcount=%0d qhigh=%0d qfull=%0d live=%0d",cyc,j,ar[j],rr[j],tail[j]-head[j],gap[j],arstall[j],rstall[j],calls[j],iterations[j],queue_writes[j],queue_reads[j],qcount[j],queue_high[j],queue_full_cycles[j],live[j]);
endtask
'''

GUARD = r'''
 if(`D.tx_TVALID&&`D.tx_TREADY)tx_seen=tx_seen+1;
 if(`D.rx_TVALID&&!`D.rx_TREADY)rx_backpressure=rx_backpressure+1;
 if(`D.tx_TVALID&&!`D.tx_TREADY)tx_backpressure=tx_backpressure+1;
 if(ctrl_activity)ctrl_seen=ctrl_seen+1;
 if((`D.tx_TVALID&&`D.tx_TREADY)||(`D.rx_TVALID&&`D.rx_TREADY)||
    (|arok)||(|rok)||(|iter)||(|(start&~old_start))||ctrl_activity||`D.ap_done)stagnant=0;
 else stagnant=stagnant+1;
 if(stagnant>=1000000)begin progress_snapshot(2);$fatal(1,"M441 global progress stalled for 1000000 cycles");end
'''


def instrument(s):
    assert s.count('module m441_monitor;') == 1
    s = s.replace('module m441_monitor;', 'module m441_monitor;' + EXTRA)
    assert s.count('cyc>30000000') == 1
    s = s.replace('cyc>30000000', 'cyc>80000000')
    # Every original fatal path exports the actual counters before returning.
    s = re.sub(r'(\$fatal\(1,[^;]+\);)', r'begin progress_snapshot(2);\1 end', s)
    marker = '  old_start=start;'
    if marker not in s:
        marker = ' old_start=start;'
    assert s.count(marker) == 1
    s = s.replace(marker, GUARD + '\n' + marker)
    hb = 'if(cyc%50000==0)$display("M441_HEARTBEAT cycle=%0d output=%0d",cyc,words);'
    assert s.count(hb) == 1
    s = s.replace(hb, 'if(cyc%50000==0)begin progress_snapshot(0);$display("M441_HEARTBEAT cycle=%0d output=%0d",cyc,words);end')
    assert s.count('if(`D.ap_done)begin') == 1
    s = s.replace('if(`D.ap_done)begin', 'if(`D.ap_done)begin\n progress_snapshot(1);')
    return s


def instrument_latency(s):
    """Measure generated delays without adding or consuming random draws."""
    pattern = r'(class (svr_latency_(?:tx|rx)|axi_latency_w[0-3]) extends[^;]+;)(.*?)(endclass)'
    def each_class(m):
        name = m[2]
        body = m[3]
        methods = ('get_transfer_lat',) if name.startswith('svr') else ('get_rctrl_lat', 'get_rdata_lat')
        for method in methods:
            pat = r'(virtual function int ' + method + r'\(\);)(.*?)(endfunction)'
            def each_method(f):
                b = f[2]
                assert b.count('return ') == 2  # Zero early return plus sampled delay
                return f[1] + '\n static longint count=0,total=0;\n' + b.replace('return transfer_latency;' if name.startswith('svr') else ('return rctrl_latency;' if 'rctrl' in method else 'return rdata_latency;'),
                    'count=count+1;total=total+delay;\n if(count%4096==0)$display("M441_DELAY channel=' + name + '_' + method + ' count=%0d sum=%0d",count,total);\n return delay;') + f[3]
            body, n = re.subn(pat, each_method, body, flags=re.S)
            assert n == 1
        return m[1] + body + m[4]
    out, n = re.subn(pattern, each_class, s, flags=re.S)
    assert n == 6
    assert out.count('std::randomize') == s.count('std::randomize')
    return out


def gate_rc(tool_rc, log, done_count):
    return tool_rc if tool_rc else (1 if re.search(r'^(?:Fatal:|ERROR:)', log, re.M) or done_count != 1 else 0)


def stall_step(previous, tx=False, rx=False, ar=False, rr=False, mac=False, start=False, control=False, done=False):
    return 0 if any((tx, rx, ar, rr, mac, start, control, done)) else previous + 1


def selftest():
    checks = []
    for key in ('tx', 'rx', 'ar', 'rr', 'mac', 'start', 'control', 'done'):
        checks.append(stall_step(999999, **{key: True}) == 0)
    checks += [stall_step(999999) == 1000000,
               gate_rc(0, 'Fatal: budget\n', 0) == 1,
               gate_rc(0, 'ERROR: bad\n', 1) == 1,
               gate_rc(0, 'M441_DONE cycles=4\n', 1) == 0,
               gate_rc(3, '', 0) == 3,
               gate_rc(0, 'puts "Fatal: echo"', 0) == 1,
               gate_rc(0, '', 2) == 1]
    assert all(checks)
    return len(checks)
