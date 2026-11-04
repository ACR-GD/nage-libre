# Reinserting / rebuilding a SNES ROM: a "don't forget anything" checklist

*English version of [`snes_reinsertion.md`](snes_reinsertion.md).*

Goes with `scripts/snes_rebuild_toolkit.py`. The order of operations for
rebuilding a modified ROM without corrupting it or skipping a step.

## The checklist

1. **Work without an SMC header.** The toolkit removes the 512-byte copier
   header automatically (`strip_smc_header`) and can add it back to the output
   with `--keep-smc`. Keep the original intact (patch a copy).
2. **Expand BEFORE writing** if the new data doesn't fit. The ROM must stay a
   multiple of 32 KB (ideally a power of two). `--expand MBIT` enlarges the ROM
   AND updates the size byte in the header.
3. **Place the data**:
   - in-place patch (same size) → `write_file` / `write_snes`;
   - bigger data → `alloc()` (looks for a free gap of 0x00/0xFF), then write
     into it. `--free-space` lists the available areas.
4. **Repoint.** If a string or asset changes size or location, update its
   pointer table (`repoint`, 2- or 3-byte pointers). Forgetting this is the
   classic cause of garbage on screen.
5. **Fix the header size byte** (`$..D7`). Done by `--expand`.
6. **Recompute the CHECKSUM + complement** (`--fix-checksum`, also done by
   `--expand` and `--build`). This is the number one thing people forget: many
   emulators and all flash carts/real consoles reject or flag a ROM with a bad
   checksum. The algorithm handles the mirroring of non-power-of-two sizes.
7. **Verify** (`--verify`): size is a multiple of 32 KB, checksum is
   consistent, complement = checksum XOR 0xFFFF, size byte is correct, and
   **no overlapping** writes (two patches overwriting each other).
8. **Distribute a patch** (`--make-ips`) rather than the ROM (legal and small).

## Reproducible rebuilds: the manifest

Instead of chaining commands, describe everything in a JSON file and run
`--build`: expansion, writes (hex / binary / fill / automatic alloc),
repointing, header + checksum fix, verification, in order, on every build.

```json
{
  "mapping": "auto",
  "expand_mbit": 16,
  "writes": [
    {"snes": "0x878000", "hex": "10 12 14 16",     "tag": "menu"},
    {"file": "0x070000", "bin": "scenes.bin",       "tag": "scenes"},
    {"alloc": true,      "bin": "police_etendue.bin","tag": "font", "align": 2}
  ],
  "repoints": [
    {"table_file": "0x8A8000", "index": 12, "target_snes": "0xC10000", "width": 3}
  ],
  "fix_checksum": true
}
```

```bash
python3 scripts/snes_rebuild_toolkit.py game.sfc --build build.json -o game_en.sfc
```

## Main commands

| Need | Command |
|---|---|
| Expand + fix header/checksum | `--expand MBIT -o out.sfc` |
| Recompute the checksum | `--fix-checksum -o out.sfc` |
| List free space | `--free-space --min 256` |
| Verify a ROM | `--verify` |
| Make an IPS patch | `--make-ips modified.sfc -o patch.ips` |
| Apply an IPS patch | `--apply-ips patch.ips -o out.sfc` |
| Full declarative rebuild | `--build manifest.json -o out.sfc` |

> For the analysis beforehand (finding text, tables, routines, graphics,
> compression) see `scripts/snes_re_toolkit.py` and
> `docs/snes_compression_id.en.md`.
