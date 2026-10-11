"""Derive exact passed collector/control; no COM3 or forward execution."""
from m351_workflow import ROOT,BASE,HERE,atomic,sha
from m421_prepare import once,PKG,OLD

def main():
    assert PKG.exists()
    s=(HERE/'m415_workflow05.py').read_text(encoding='utf-8')
    s=s.replace("PKG=BASE/'candidates/M415-saved-feature-language-04'","PKG=BASE/'candidates/M421-combination-saved-language-01'")
    s=s.replace("OUT=BASE/'runs/M415-saved-feature-language-board-03/BOARD_RESULT.json'","OUT=BASE/'runs/M421-saved-language-board-01/BOARD_RESULT.json'")
    s=s.replace('M415','M421').replace('m415','m421').replace('layer12_candidate','layer12_13_candidate').replace('M414','M420').replace('第12层','第12＋13层')
    s=once(s,"BASE/'candidates/M421-saved-feature-language-03/PACKAGE_MANIFEST.json'","BASE/'candidates/M415-saved-feature-language-04/PACKAGE_MANIFEST.json'")
    s=s.replace("ROOT/'tmp/m42104'","ROOT/'tmp/m42101'").replace('runs/M421-saved-feature-transfer-04','runs/M421-saved-language-transfer-01')
    s=s.replace('latest_m421_saved_feature_language_board','latest_m421_saved_language_board').replace('latest_m421_saved_feature_transfer','latest_m421_saved_language_transfer')
    anchor="    if r['performance_pass'] or r['formal_promotion_allowed']"
    at=s.index(anchor)
    s=s[:at]+"    if r.get('features_verified_before_overlay') is True and (r.get('selected_layers')!=[12,13] or r.get('saved_feature_source_sha256')!=plan['M420_raw_sha256'] or r.get('saved_feature_identities')!=[dict(path=plan['feature_directory']+'/'+x['path'],file_sha256=x['file_sha256'],tensor=x['tensor']) for x in plan['features']]):raise ValueError('M420 source/layers/retained features differ')\n"+s[at:]
    atomic(HERE/'m421_workflow.py',s.encode('utf-8'),immutable=True)
    s=(HERE/'m415_control05.ps1').read_text(encoding='utf-8')
    s=s.replace('M415-saved-feature-language-04','M421-combination-saved-language-01').replace('M415-saved-feature-language-03','__BORROWED_M415_04__')
    s=s.replace('m415','m421').replace('M415','M421')
    s=s.replace('__BORROWED_M421_04__','M415-saved-feature-language-04').replace('__BORROWED_M415_04__','M415-saved-feature-language-04')
    s=s.replace('m421_saved_feature_candidate_04','m421_saved_feature_candidate_01').replace('tmp/m42104','tmp/m42101').replace('m421_workflow05.py','m421_workflow.py')
    s=s.replace('M421-saved-feature-language-board-03','M421-saved-language-board-01').replace('latest_m421_saved_feature_preparation','latest_m421_saved_language_preparation').replace('latest_m421_saved_feature_support','latest_m421_saved_language_support').replace('latest_m421_saved_feature_transfer','latest_m421_saved_language_transfer')
    s=once(s,"'latest_m414_layer12_visual_board','latest_m414_layer12_visual_closure','latest_m368_video_closure'","'latest_m420_combination_board','latest_m420_combination_closure','latest_m415_saved_feature_language_board','latest_m368_video_closure'")
    # Upload sudo timestamp refreshed only through successful sudo-n; never passwords.
    anchor='        "M421_FILE_TRANSFERRED $name"'
    s=once(s,anchor,anchor+"\n        & $uart -Command 'sudo -n true' -LogPath \"tmp/m42101/refresh_$($name.Replace('.','_')).log\" -TimeoutSeconds 15 -MarkerPrefix '__M421_SUDO_RC_'\n        if (-not $?) { throw 'Sudo expired; upload stopped' }")
    atomic(HERE/'m421_control.ps1',s.encode('utf-8'),immutable=True)
    print('M421_HOST_PREPARED',sha(HERE/'m421_workflow.py'),sha(HERE/'m421_control.ps1'))
if __name__=='__main__':main()
