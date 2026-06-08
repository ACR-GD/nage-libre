import sys
with open('build_patched_rom.py', 'r') as f:
    content = f.read()

import re
content = re.sub(r'def assemble_hook\(.*', '', content, flags=re.DOTALL)

with open('build_patched_rom.py', 'w') as f:
    f.write(content)
