"""Real frozen tokenizer loader reuse -> original request boundary, CPU only."""
import ast,hashlib,json,sys
from pathlib import Path
import tokenizers
from m363_tokenizer_once import ValidatedTokenizerOnce
from m363_observers import tokenizer_proxy
from m351_workflow import ROOT,BASE,atomic,encoded,sha
def main():
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    d=release/'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate'
    prompt=d/'m276_prompt_contract.py';views=d/'m273_latest_multiscale_contract.py'
    names={'IMAGE_PAD','VISION_START','VISION_END','VIEW_COUNT','VISUAL_TOKENS_PER_VIEW'};namespace={'Path':Path}
    for n in ast.parse(views.read_text(encoding='utf-8')).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names:namespace[n.targets[0].id]=ast.literal_eval(n.value)
    tree=ast.parse(prompt.read_text(encoding='utf-8'))
    code=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ('render','tokenize')) or (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='M276_KNIFE_PROMPT')]
    exec(compile(ast.Module(body=code,type_ignores=[]),str(prompt),'exec'),namespace)
    file=release/'deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json'
    expected=json.loads((BASE/'candidates/M415-saved-feature-language-04/VISUAL_EXPECTED.json').read_bytes())['prompt_token_ids']
    before=sha(file);original=tokenizers.Tokenizer;once=ValidatedTokenizerOnce(original.from_file)
    try:
        tokenizers.Tokenizer=tokenizer_proxy(original,once.from_file)
        validated=tokenizers.Tokenizer.from_file(str(file));loaded=tokenizers.Tokenizer.from_file(str(file))
        assert validated is loaded and once.parse_count==once.reuse_count==1 and once.cached is None
        rejected=False
        try:namespace['tokenize'](file,namespace['M276_KNIFE_PROMPT'],3.0)
        except RuntimeError as exc:rejected=str(exc)=='Unexpected additional tokenizer parse'
        assert rejected
        tokenizers.Tokenizer=original
        ids=namespace['tokenize'](file,namespace['M276_KNIFE_PROMPT'],3.0)
        assert ids==expected and len(ids)==159 and sha(file)==before
    finally:tokenizers.Tokenizer=original
    assert 'pynq' not in sys.modules
    r=dict(status='PASS_M415_ACTUAL_FROZEN_TOKENIZER_RESTORE_COMPONENT',real_tokenizers_library=tokenizers.__version__,
        actual_tokenizer_file_sha256=before,actual_tokenizer_bytes=file.stat().st_size,actual_prompt_function_source_sha256=sha(prompt),view_source_sha256=sha(views),
        actual_single_parse_original_loader_same_object=True,actual_missing_restore_failure_reproduced=True,
        restored_original_request_parse=True,exact159_original_token_ids=True,tokenizer_class_restored=True,
        no_Overlay_DMA_vision_or_language=True,WSL_CPU_only_not_board_quality=True)
    out=BASE/'runs/M415-tokenizer-component-07/RESULT.json';atomic(out,encoded(r),immutable=True)
    print('M415_TOKENIZER_COMPONENT_PASS',sha(out))
if __name__=='__main__':main()
