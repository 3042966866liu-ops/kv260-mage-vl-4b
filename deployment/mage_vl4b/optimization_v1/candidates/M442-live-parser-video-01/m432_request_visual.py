"""Late11 full-request numerical provider; the original runtime owns all DMA."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources(plan):
    from m428_saved_features import read_owned
    if plan['selected_layers'] != list(range(13, 24)) or plan['extra_DMA'] != 0 or plan['temperature_measurement_enabled']:
        raise RuntimeError('Frozen late11 scope required')
    result = {}
    for name, entry in plan['integrated_sources'].items():
        r = json.loads(read_owned(Path(entry['path']), entry['bytes'], entry['sha256']))
        if r['status'] != entry['status'] or type(r['gate_return_code']) is not int or r['gate_return_code'] or r['errors']:
            raise RuntimeError('Integrated prerequisite status/rc differs')
        result[name] = r
    if set(result) != {'visual', 'language', 'software', 'CPU'}:
        raise RuntimeError('All accepted integrated prerequisites required')
    v, l, s, c = (result[k] for k in ('visual', 'language', 'software', 'CPU'))
    if (v['selected_layers'] != list(range(13, 24)) or not v['safe_buffers_released'] or not v['stable_restored']
            or not v['numerical_hardware_proven'] or v['matched_wire_batches'] != 286 or v['language_forward_calls']):
        raise RuntimeError('Complete visual numerical prerequisite differs')
    if (l['selected_layers'] != list(range(13, 24)) or not l['safe_buffers_released'] or not l['stable_overlay_reloaded']
            or not l['original_reference_pass'] or not l['decision_consistency_pass'] or l['vision_forward_calls'] or len(l['samples']) != 2):
        raise RuntimeError('Saved language numerical prerequisite differs')
    if s['feature_pass_ranges'] != ['late_13_23'] or not s['bindings_restored'] or not s['visual_owner_closed']:
        raise RuntimeError('Accepted software range differs')
    if (c['manifest_sha256'] != plan['CPU_manifest_sha256'] or c['source_identities_verified'] != 49
            or any(c[k] for k in ('overlay_loads', 'DMA_allocations', 'real_model_forward_calls', 'FPGA_transactions', 'temperature_measurement_enabled'))
            or c['component']['window']['complete_batches'] != 286 or c['component']['window']['staged_windows'] != 22):
        raise RuntimeError('Borrowed CPU capability prerequisite differs')
    for row in plan['visual_reused_packages']:
        folder = Path(row['directory'])
        if digest(folder / 'PACKAGE_MANIFEST.json') != row['manifest_sha256']:
            raise RuntimeError('Visual package manifest differs')
        manifest = json.loads((folder / 'PACKAGE_MANIFEST.json').read_bytes())
        names = {e['path'] for e in manifest['files']}
        if ({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} != names | {'PACKAGE_MANIFEST.json'}
                or len(names) != manifest['file_count'] or sum(e['bytes'] for e in manifest['files']) != manifest['total_bytes']):
            raise RuntimeError('Visual package closure differs')
        for entry in manifest['files']:
            p = folder / entry['path']
            if p.is_symlink() or p.stat().st_size != entry['bytes'] or digest(p) != entry['sha256']:
                raise RuntimeError('Visual support payload differs')
    return result


class VisualProvider:
    def __init__(self, engine, runtime, policy, base, here, result, sources):
        self.engine, self.runtime, self.policy, self.base, self.result = engine, runtime, policy, base, result
        self.sources, self.current_owner, self.current_scope, self.disposed = sources, None, None, False
        self.plan = json.loads((here / 'PLAN.json').read_bytes())
        sys.path[1:1] = [x['directory'] for x in self.plan['visual_reused_packages']]
        import torch
        from frozen_video_identity import RELEASE, FRAMES, ADDON, STACK_SHA
        from m273_latest_multiscale_contract import preprocess
        from m206_ps_vision_runtime import M206ProgressLayer
        from ps_vision_runtime import M196PrecisionBoundary
        from m207_ps_vision_runtime import M207FP32GemmW4Linear
        from m426_range02 import resolve, prefix_evidence
        from test_m409_ftz_reference import actual_host
        from m407_mlp_contract import chain_for
        from m429_pl_range import SavedWireCheck
        self.torch, self.root = torch, RELEASE
        self.host, self.initial = actual_host(RELEASE)
        self.targets, target_ids = resolve(engine.vision.vision, M206ProgressLayer, M196PrecisionBoundary, M207FP32GemmW4Linear, torch)
        prefix = prefix_evidence(engine.vision.vision, M206ProgressLayer, M196PrecisionBoundary, M207FP32GemmW4Linear, torch)
        if target_ids != sources['visual']['targets'] or prefix != sources['visual']['prefix_topology']:
            raise RuntimeError('Actual complete-runtime visual topology/matrices differ')
        vbase = RELEASE / 'deployment/mage_vl4b/m181_m120_video_board_candidate'
        layout_path = vbase / 'vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
        if digest(layout_path) != self.plan['layout_sha256']:
            raise RuntimeError('Frozen W4 layout differs')
        layout = json.loads(layout_path.read_bytes())
        if [x['path'] for x in layout['files']] != ['weights0.bin', 'weights1.bin', 'weights2.bin', 'weights3.bin']:
            raise RuntimeError('Original shard order differs')
        for row in layout['files']:
            p = vbase / 'vision_layout' / row['path']
            if p.is_symlink() or p.stat().st_size != row['bytes'] or digest(p) != row['sha256']:
                raise RuntimeError('Full frozen shard SHA differs')
        entries = {e['module']: e for e in layout['modules']}
        self.cases, self.windows = {}, {}
        for index in range(13, 24):
            self.cases[index], self.windows[index] = {}, {}
            for j, part in enumerate(('fc1', 'fc2')):
                c = chain_for(entries[f'model.visual.encoder.layers.{index}.mlp.{part}'], index * 2 + j)
                if c != self.plan['chains'][str(index)][part]:
                    raise RuntimeError('Full chain ABI differs')
                self.cases[index][part] = c
                self.windows[index][part] = [dict(row, relative_file='deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/' + row['path']) for row in self.plan['windows'][str(index)][part]]
        matches = [x for x in sources['software']['ranges'] if x['name'] == 'late_13_23']
        if len(matches) != 1:
            raise RuntimeError('Unique accepted software reference required')
        self.accepted = matches[0]
        self.reference = self.accepted['reference_batches']
        SavedWireCheck(self.reference, lambda *unused: None)
        frames = []
        for name, expected in FRAMES.items():
            p = ADDON / 'fixtures' / name
            if digest(p) != expected:
                raise RuntimeError('Fixed frame SHA differs')
            frames.append(np.load(p, allow_pickle=False))
        self.frames = np.ascontiguousarray(np.stack(frames))
        if self.frames.shape != (4, 448, 448, 3) or self.frames.dtype != np.uint8 or hashlib.sha256(self.frames.tobytes()).hexdigest() != STACK_SHA:
            raise RuntimeError('Ordered frame stack differs')
        self.preprocess = preprocess
        result.update(visual_staging=[], integrated_visual=[], visual_transactions=[], borrowed_extra_DMA=0)

    def __call__(self, index):
        from m431_borrowed_visual import BorrowedVisual
        from m429_pl_range import PLRangeScope, SavedWireCheck
        from m428_saved_features import tensor
        if index != 1 or len(self.result['integrated_visual']) != 0 or self.result.get('language_scope_active', False) or self.disposed:
            raise RuntimeError('One accepted late11 fixed request only')
        self.policy.capture('before-integrated-visual:' + str(index), True)
        tensors = self.preprocess(np.ascontiguousarray(self.frames[-1:]))
        if {k: tensor(v) for k, v in sorted(tensors.items())} != self.sources['visual']['preprocessed']:
            raise RuntimeError('Fixed preprocess differs')
        owner = scope = guard = None
        def forward():
            self.result['vision_request_active'] = True
            try:
                return self.engine.vision(tensors['pixel_values'], tensors['image_grid_thw'], tensors['patch_positions'])
            finally:
                self.result['vision_request_active'] = False
        try:
            if index == 0:
                visual = forward()
            else:
                with BorrowedVisual(self.runtime, self.policy, self.base, self.result, enabled=True,
                                    language_active=lambda: self.result.get('language_scope_active', False)) as owner:
                    self.current_owner = owner
                    guard = SavedWireCheck(self.reference, owner.submit)
                    def sink(layer, arr):
                        if tensor(arr) != self.accepted['boundary_comparison'][layer]['candidate']:
                            raise RuntimeError('Full accepted visual boundary differs:' + str(layer))
                        self.result.setdefault('integrated_boundaries', []).append(dict(layer=layer, tensor=tensor(arr)))
                    scope = PLRangeScope(self.torch, self.engine.vision.vision.encoder.layers, self.targets,
                                         lambda i: dict(chains=self.cases[i]), self.initial, self.host, sink,
                                         lambda label: self.policy.capture(label, True),
                                         lambda i, part, c: owner.stage(i, part, c, self.windows[i][part], self.root), guard)
                    self.current_scope = scope
                    with scope:
                        visual = forward()
                    guard.require_complete()
                if (not scope.complete or not scope.restored or scope.peak_live_layer_scopes != 1
                        or owner.retained or owner.entered or len(owner.rows) != 286 or len(owner.staging) != 22
                        or sum(row['bytes'] for row in owner.staging) != 49020928):
                    raise RuntimeError('Borrowed complete visual lifecycle incomplete')
                self.result.update(visual_staging=owner.staging, borrowed_buffer_identity_preserved=True,
                                   visual_static_cache_invalidated=self.runtime._programmed_config is None and self.runtime._programmed_weight_addresses is None,
                                   visual_bindings_restored=scope.restored, peak_live_visual_layer_scopes=scope.peak_live_layer_scopes,
                                   visual_matched_wire_batches=len(guard.seen))
            if tensor(visual) != self.plan['features'][index]['tensor']:
                raise RuntimeError('Complete original/candidate visual feature differs')
            self.result['integrated_visual'].append(tensor(visual))
            self.policy.capture('after-integrated-visual:' + str(index), True)
            self.current_owner = self.current_scope = None
            print('M442V_VISUAL_EXACT_PASS ' + str(index), flush=True)
            return visual
        finally:
            if owner is not None and (owner.retained or self.policy.active):
                self.current_owner = owner

    def dispose(self):
        if self.current_owner is not None or self.current_scope is not None or self.result.get('language_scope_active', False):
            raise RuntimeError('Cannot dispose active or unclosed borrowed visual owner/scope')
        for name in ('engine', 'runtime', 'policy', 'base', 'targets', 'frames', 'cases', 'windows', 'sources', 'reference', 'host', 'accepted'):
            setattr(self, name, None)
        self.disposed = True
        self.result['visual_provider_disposed'] = True
