import hashlib,json,sys
from pathlib import Path
task_root=Path(__file__).resolve().parent
task_manifest=task_root/'PACKAGE_MANIFEST.json'
if len(sys.argv)!=2 or hashlib.sha256(task_manifest.read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Recovery manifest differs')
task_rows=json.loads(task_manifest.read_text(encoding='utf-8'))['files']
if [r['path'] for r in task_rows]!=['export_saved.py','SHA256SUMS']:raise RuntimeError('Recovery whitelist differs')
for task_row in task_rows:
    task_file=task_root/task_row['path']
    if task_file.stat().st_size!=task_row['bytes'] or hashlib.sha256(task_file.read_bytes()).hexdigest()!=task_row['sha256']:raise RuntimeError('Recovery payload differs')
if {p.name for p in task_root.iterdir()}!={'PACKAGE_MANIFEST.json','export_saved.py','SHA256SUMS'}:raise RuntimeError('Recovery directory differs')
RAW_SHA='dbd3325e8152bf24402ce616b7fad4fe0584a4e7972aae573fb245a4eb52abaf'
MISSING=[2481, 2482, 2544, 2548, 2551, 2554, 2558, 2561, 2565, 2568, 2575, 2578, 2582, 2585, 2589, 2592, 2605, 2606, 2609, 2616, 2619, 2622, 2623, 2626, 2629, 2630, 2633, 2640, 2643, 2650, 2653, 2654, 2657, 2661, 2664, 2668, 2671, 2672, 2675, 2678, 2679, 2682, 2685, 2686, 2689, 2692, 2693, 2696, 2700, 2703, 2707, 2710, 2714, 2717, 2718, 2721, 2724, 2728, 2731, 2735, 2738, 2742, 2745, 2749, 2752, 2753, 2756, 2759, 2760, 2763, 2767, 2770, 2771, 2774, 2777, 2778, 2781, 2785, 2788, 2789, 2792, 2796, 2799, 2800, 2803, 2806, 2807, 2810, 2811, 2817, 2818, 2821, 2825, 2829, 2832, 2836, 2840, 2843, 2844, 2847, 2851, 2852, 2865, 2868, 2872, 2875, 2876, 2879, 2883, 2886, 2887, 2890, 2894, 2897, 2898, 2901, 2904, 2905, 2908, 2912, 2915, 2916, 2919, 2923, 2926, 2927, 2930, 2934, 2937, 2938, 2941, 2945, 2949, 2952, 2953, 2956, 2960, 2964, 2967, 2968, 2971, 2972]
import base64,hashlib,os,time
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('Root required')
raw=Path('/home/ubuntu/m368_staged_video_02/B1/load-memory.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=RAW_SHA:raise RuntimeError('Original saved SHA differs')
parts=[raw[i:i+900] for i in range(0,len(raw),900)]
if len(parts)!=2975:raise RuntimeError('Original chunk count differs')
print('M368_RECOVERY_SHA='+RAW_SHA,flush=True)
for i in MISSING:
    print(f'M368_RECOVERY_CHUNK={i}/2975:'+base64.b64encode(parts[i]).decode(),flush=True)
    time.sleep(.12)
print('M368_RECOVERY_DONE_NO_GATE',flush=True)
