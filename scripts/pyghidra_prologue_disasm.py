#!/usr/bin/env python3
"""PyGhidra: désassemble les routines du prologue (Bank $87 / $80)."""
import os
from pathlib import Path

os.environ.setdefault(
    "GHIDRA_INSTALL_DIR",
    "/opt/homebrew/Cellar/ghidra/12.1.1/libexec",
)

import pyghidra

pyghidra.start()

from ghidra.program.model.lang import LanguageID
from ghidra.program.database import ProgramDB
from ghidra.program.util import DefaultLanguageService
from ghidra.program.flatapi import FlatProgramAPI
from ghidra.util.task import TaskMonitor
import java.lang.Object

ROM = Path(__file__).resolve().parent.parent / "Nage Libre - Seijaku no Suishin (Japan).sfc"

TARGETS = [
    ("New Game → prologue", 0x80938C),
    ("Scene decompress hook", 0x8380FF),
    ("Scene decompressor", 0x80F8D8),
    ("Prologue driver", 0x87D63B),
    ("Table copy DA0E", 0x87DA0E),
    ("Cloud text DA3B", 0x87DA3B),
    ("Text engine F4AB", 0x80F4AB),
    ("Load $87:896D", 0x87D990),
    ("Load $87:89C5", 0x87EA36),
    ("Load $87:89DF", 0x87EA46),
]


def main() -> None:
    lang = DefaultLanguageService.getLanguageService().getLanguage(
        LanguageID("65816:LE:16:default")
    )
    consumer = java.lang.Object()
    prog = ProgramDB("Nage_Libre_Prologue", lang, lang.getDefaultCompilerSpec(), consumer)
    api = FlatProgramAPI(prog)
    rom = ROM.read_bytes()

    tx = prog.startTransaction("map")
    try:
        for bank in range(0x80, 0x100):
            ro = (bank - 0x80) * 0x8000
            if ro >= len(rom):
                break
            addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress(
                (bank << 16) | 0x8000
            )
            prog.getMemory().createInitializedBlock(
                f"ROM_{bank:02X}", addr, 0x8000, 0, TaskMonitor.DUMMY, False
            )
            prog.getMemory().setBytes(addr, rom[ro : ro + 0x8000])

        for label, snes in TARGETS:
            a = prog.getAddressFactory().getDefaultAddressSpace().getAddress(snes)
            api.disassemble(a)
            print(f"\n=== {label} @ ${snes:06X} ===")
            ins = prog.getListing().getInstructionAt(a)
            for _ in range(28):
                if ins is None:
                    break
                print(f"  {ins.getAddress()}  {ins}")
                ins = ins.getNext()
    finally:
        prog.endTransaction(tx, True)
        prog.release(consumer)


if __name__ == "__main__":
    main()
