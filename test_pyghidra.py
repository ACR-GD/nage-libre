import pyghidra

pyghidra.start()

from ghidra.program.model.lang import LanguageService

language_service = LanguageService.getLanguageService()
languages = language_service.getLanguageDescriptions(False)

snes_found = False
for lang in languages:
    lang_id = lang.getLanguageID().getIdAsString()
    if "65816" in lang_id or "SNES" in lang_id.upper():
        print(f"Found language: {lang_id}")
        snes_found = True
        
if not snes_found:
    print("No 65816/SNES language found.")
