import sys

with open('build_patched_rom.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_dict = False
dict_ended = False

for line in lines:
    if line.startswith('    73: "O Orb",'):
        new_lines.append(line)
        new_lines.append('}\n\n')
        new_lines.append('PROLOGUE_LINES = []\n\n')
        dict_ended = True
    else:
        new_lines.append(line)

with open('build_patched_rom.py', 'w') as f:
    f.writelines(new_lines)
