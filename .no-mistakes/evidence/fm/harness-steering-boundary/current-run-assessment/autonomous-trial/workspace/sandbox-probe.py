from pathlib import Path
import json,sys
inside=Path(sys.argv[1]); outside=Path(sys.argv[2])
inside.write_text('allowed')
try:
 outside.write_text('must be denied')
except PermissionError:
 print(json.dumps({'inside_write':True,'outside_write_denied':True}))
else:
 raise SystemExit('unsafe: outside write succeeded')
