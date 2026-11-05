import argparse,http.server,functools
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=5173);a,_=p.parse_known_args()
root=Path(__file__).resolve().parents[1]/'docs'
print(f'http://{a.host}:{a.port}',flush=True)
http.server.ThreadingHTTPServer((a.host,a.port),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root))).serve_forever()
