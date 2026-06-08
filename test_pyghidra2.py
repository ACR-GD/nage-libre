import pyghidra
import os

with pyghidra.start():
    # Attempt to import LanguageService to see available languages
    from ghidra.program.util import DefaultLanguageService
    
    lang_service = DefaultLanguageService.getLanguageService()
    langs = lang_service.getLanguageDescriptions(False)
    
    snes_lang = None
    for l in langs:
        id_str = l.getLanguageID().getIdAsString()
        if "65816" in id_str or "SNES" in id_str.upper():
            print(f"Found: {id_str}")
            snes_lang = l.getLanguageID()
            break
            
    if snes_lang:
        print(f"Using language: {snes_lang}")
    else:
        print("No SNES language found.")
