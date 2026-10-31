"""Cross-language packet fixture check; no Windows audio endpoint needed."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/controller/server'))
from libs.pc_stream import encode_packet
expected=encode_packet(bytes(range(32)),bytes(range(16)),7,48000,bytes([0,128,255,127,0,0,1,0]))
assert Path(sys.argv[1]).read_bytes()==expected,'Windows sender/Python receiver packet mismatch'
print('C#/Python signed PCM packet interoperability passed.')
