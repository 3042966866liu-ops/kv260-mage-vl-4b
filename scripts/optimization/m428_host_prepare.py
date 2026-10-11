"""Derive existing passed host checks; precise source/path replacements."""
from m351_workflow import HERE, atomic, sha
from m428_prepare02 import once


def main():
    w = (HERE / 'm421_workflow.py').read_text(encoding='utf-8')
    w = w.replace('m421', 'm428').replace('M421', 'M428').replace('layer12_13_candidate', 'late13_23_candidate')
    w = once(w, 'M428-combination-saved-language-01', 'M428-late11-saved-language-02')
    w = once(w, 'M415-saved-feature-language-04/PACKAGE_MANIFEST.json', 'M421-combination-saved-language-01/PACKAGE_MANIFEST.json')
    w = once(w, "r.get('selected_layers')!=[12,13]", "r.get('selected_layers')!=plan['selected_layers']")
    w = once(w, "plan['M420_raw_sha256']", "plan['M427_raw_sha256']")
    w = once(w, "plan['feature_directory']+'/'+x['path']", "plan['feature_directories'][x['source']]+'/'+x['path']")
    w = w.replace('M420 source/layers/retained features differ', 'M427 accepted late11 source/layers/retained features differ')
    w = once(w, "if r['performance_pass'] or r['formal_promotion_allowed']", "if r.get('temperature_measurement_enabled') is not False:raise ValueError('Temperature measurement forbidden')\n    if r['performance_pass'] or r['formal_promotion_allowed']")
    w = w.replace('只复用M420原版和第12＋13层候选98×2560特征', '只复用M426保存原版和M427后11层候选98×2560特征')
    w = w.replace('原M420两份特征', '保存原版与已通过特征筛查的后11层候选')
    atomic(HERE / 'm428_workflow.py', w.encode('utf-8'), immutable=True)
    c = (HERE / 'm421_control.ps1').read_text(encoding='utf-8')
    c = c.replace('m421', 'm428').replace('M421', 'M428')
    c = once(c, 'M428-combination-saved-language-01', 'M428-late11-saved-language-02')
    c = once(c, 'M415-saved-feature-language-04/PACKAGE_MANIFEST.json', 'M421-combination-saved-language-01/PACKAGE_MANIFEST.json')
    c = once(c, "'latest_m420_combination_board','latest_m420_combination_closure','latest_m415_saved_feature_language_board'", "'latest_m427_half_software_board','latest_m427_half_closure','latest_m421_saved_language_board'")
    atomic(HERE / 'm428_control.ps1', c.encode('utf-8'), immutable=True)
    print('M428_HOST_PREPARED', sha(HERE / 'm428_workflow.py'), sha(HERE / 'm428_control.ps1'))


if __name__ == '__main__':
    main()
