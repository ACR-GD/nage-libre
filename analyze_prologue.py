import os
import sys
os.environ['GHIDRA_INSTALL_DIR'] = '/opt/homebrew/Cellar/ghidra/12.1.1/libexec'
import pyghidra
pyghidra.start()

from ghidra.program.model.lang import LanguageID
from ghidra.program.database import ProgramDB
from ghidra.program.util import DefaultLanguageService
from ghidra.program.flatapi import FlatProgramAPI
from ghidra.util.task import TaskMonitor
import java.lang.Object

lang = DefaultLanguageService.getLanguageService().getLanguage(LanguageID("65816:LE:16:default"))
compiler = lang.getDefaultCompilerSpec()

consumer = java.lang.Object()
prog = ProgramDB("Nage_Libre", lang, compiler, consumer)
api = FlatProgramAPI(prog)

rom_path = "Nage Libre - Seijaku no Suishin (Japan).sfc"
with open(rom_path, 'rb') as f:
    rom_bytes = f.read()

transaction = prog.startTransaction("Map Memory")
try:
    for bank in range(0x80, 0x100):
        rom_offset = (bank - 0x80) * 0x8000
        if rom_offset >= len(rom_bytes):
            break
        
        bank_bytes = rom_bytes[rom_offset:rom_offset+0x8000]
        addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress( (bank << 16) | 0x8000 )
        prog.getMemory().createInitializedBlock(f"ROM_{bank:02X}", addr, len(bank_bytes), 0, TaskMonitor.DUMMY, False)
        prog.getMemory().setBytes(addr, bank_bytes)
        
    print("Memory mapped.")
    
    start_dis = prog.getAddressFactory().getDefaultAddressSpace().getAddress(0x87EA20)
    api.disassemble(start_dis)
    print("Disassembled EA20.")
    
    ins = prog.getListing().getInstructionAt(start_dis)
    for i in range(30):
        if not ins:
            break
        print(f"{ins.getAddress()} {ins}")
        ins = ins.getNext()
        
finally:
    prog.endTransaction(transaction, True)
    prog.release(consumer)
