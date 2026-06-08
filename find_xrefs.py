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

    # Search for byte pattern of LDA #$89C5
    # LDA #$89C5 = A9 C5 89
    target_bytes = [0xA9, 0xC5, 0x89]
    found = api.findBytes(api.toAddr(0x808000), bytes(target_bytes), 10, 1)
    for addr in found:
        print("Found A9 C5 89 at:", addr)
        # Disassemble around it
        start_dis = api.toAddr(addr.getOffset() - 10)
        api.disassemble(start_dis)
        ins = prog.getListing().getInstructionAt(start_dis)
        for i in range(10):
            if not ins: break
            print(f"  {ins.getAddress()} {ins}")
            ins = ins.getNext()
            
finally:
    prog.endTransaction(transaction, True)
    prog.release(consumer)
