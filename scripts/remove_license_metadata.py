"""One-time cleanup of stored paper data; normal writes also drop these fields."""
import hashlib
import json
from common import ROOT,without_license_metadata,load,write


def main():
    changed=[]
    for root in (ROOT/'work',ROOT/'docs/data'):
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix not in ('.json','.js'):continue
            raw=path.read_text()
            prefix=''
            try:
                if path.suffix=='.js':
                    prefix,body=raw.split('=',1);data=json.loads(body.strip().rstrip(';'))
                else:data=json.loads(raw)
            except (ValueError,UnicodeError):continue
            clean=without_license_metadata(data)
            if clean==data:continue
            if prefix:path.write_text(prefix+'= '+json.dumps(clean,ensure_ascii=False,indent=2)+';\n')
            else:write(path,clean)
            changed.append(str(path.relative_to(ROOT)))
    index_path=ROOT/'docs/data/archive-index.json';index=load(index_path)
    for entry in index['issues']:
        path=ROOT/'docs'/entry['path']
        entry['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    write(index_path,index)
    write(ROOT/'work/license-removal-report.json',{'changed_files':changed})
    print('Removed license metadata from',len(changed),'saved files')

if __name__=='__main__':main()
