import pyghidra
pyghidra.start()

from ghidra.program.util import DefaultLanguageService
lang_service = DefaultLanguageService.getLanguageService()
for l in lang_service.getLanguageDescriptions(False):
    if "65" in l.getLanguageID().getIdAsString():
        print(l.getLanguageID().getIdAsString())
