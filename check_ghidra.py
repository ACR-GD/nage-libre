import os
os.environ['GHIDRA_INSTALL_DIR'] = '/opt/homebrew/Cellar/ghidra/12.1.1/libexec'
import pyghidra
pyghidra.start()
from ghidra.program.util import DefaultLanguageService
langs = DefaultLanguageService.getLanguageService().getLanguageDescriptions(False)
found_snes = False
for l in langs:
    s = l.getLanguageID().toString().lower()
    if '65816' in s or 'snes' in s:
        print("Found:", s)
        found_snes = True

if not found_snes:
    print("No 65816 or SNES processor found.")
