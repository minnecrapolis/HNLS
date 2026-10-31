"""Check that a frozen scoped payload reaches current source through guarded updates."""
import hashlib,json

def assert_lineage(case,root,name,start):
    current=hashlib.sha256((root/'src/controller'/name).read_bytes()).hexdigest()
    edges={}
    for manifest in (root/'updates').glob('*/manifest.json'):
        value=json.loads(manifest.read_text()).get(name)
        if value:
            for parent in value['supported']:
                edges.setdefault(parent,set()).add(value['sha256'])
    todo=[start];seen=set()
    while todo:
        digest=todo.pop()
        if digest==current:return
        if digest in seen:continue
        seen.add(digest);todo.extend(edges.get(digest,()))
    case.fail('No guarded update ancestry for '+name)
