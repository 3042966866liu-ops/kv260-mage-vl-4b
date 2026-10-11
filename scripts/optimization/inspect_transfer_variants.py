import ast
import hashlib
import io
import json
from pathlib import Path
import tokenize

root=Path(__file__).resolve().parents[2]
for directory in ('deployment/mage_vl4b','tmp/m176_fixed_text'):
    for path in (root/directory).rglob('board_runtime.py'):
        source=path.read_text(encoding='utf-8')
        for node in ast.parse(source).body:
            if not isinstance(node,ast.FunctionDef) or node.name!='copy_window_to_buffer':continue
            text=ast.get_source_segment(source,node)
            tokens=[(tokenize.tok_name[t.type],t.string) for t in tokenize.generate_tokens(io.StringIO(text).readline)
                    if t.type not in (tokenize.COMMENT,tokenize.NL,tokenize.NEWLINE,tokenize.ENDMARKER)]
            digest=hashlib.sha256(json.dumps(tokens,separators=(',',':')).encode()).hexdigest()
            print(digest,path.relative_to(root))
            if digest=='d32142ccf13551624695bce7a057297a2abb34183779a73872669433415ec1b5':print(text)
