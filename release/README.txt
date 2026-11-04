===============================================================================
  NAGE LIBRE: SEIJAKU NO SUISHIN  -  English Translation  v1.0
  Super Famicom  -  Varie, 1995
  Patch released 2026-11-04
  https://github.com/ACR-GD/nage-libre
===============================================================================

CONTENTS
  1. About the game
  2. About this translation (please read)
  3. What is translated
  4. How to patch
  5. ROM information
  6. Known issues and choices
  7. Reporting mistakes
  8. Credits
  9. Disclaimer


-------------------------------------------------------------------------------
1. ABOUT THE GAME
-------------------------------------------------------------------------------
Nage Libre: Seijaku no Suishin was released by Varie for the Super Famicom on
February 24, 1995, and never left Japan.

Five schoolgirls are pulled from an ordinary morning into a strange world
called "Nage", and have to fight their way home. Between story scenes, you
move your party around stage maps and settle every fight with a card battle:
attack, defend, heal, swap cards and pull off special moves. The club each
girl joins changes her abilities, and the birthday you enter for each girl
gives her a birthstone.

A sequel, Nage Libre: Rasen no Soukoku, came out on the PlayStation in 1997.
This patch is for the Super Famicom game only.


-------------------------------------------------------------------------------
2. ABOUT THIS TRANSLATION (PLEASE READ)
-------------------------------------------------------------------------------
This is my first fan translation.

It was made with the help of AI. An AI model (Anthropic's Claude) helped me
decode the game's text and font, write the tools that put the English text
into the ROM, and draft the English script.

I then proofread the whole script myself, every line of story dialogue, and
rewrote the lines that were wrong or read badly (87 corrections in the final
pass). I also played the game to check the text on screen.

So: AI-assisted, human-proofread. I did my best, but I am one person and
mistakes are probably still in there: a misread line, an odd phrasing, a
name read the wrong way. If you spot one, please tell me (see section 7).
Every report makes the next version better.


-------------------------------------------------------------------------------
3. WHAT IS TRANSLATED
-------------------------------------------------------------------------------
  - All story dialogue (about 2,300 lines), including the prologue, the
    ending and the staff credits
  - Menus: title, file select, save/load, birthday entry, club select, shop,
    card swap, stage preparation
  - Card battles: commands, all battle messages, level-ups and stat gains
  - The PAGER command windows
  - All character and enemy names, club names and birthstones

Dialogue boxes keep the game's original 3-line layout, with the English
drawn two letters per Japanese character cell.


-------------------------------------------------------------------------------
4. HOW TO PATCH
-------------------------------------------------------------------------------
Two patches are included. They produce the same ROM.

  Nage Libre - Seijaku no Suishin (English v1.0).bps   <- recommended
  Nage Libre - Seijaku no Suishin (English v1.0).ips   <- for tools/flash
                                                         carts that need IPS

Easiest: open https://www.marcrobledo.com/RomPatcher.js/ , pick your ROM and
the .bps file, and click "Apply patch". On a computer you can also use
Floating IPS (Flips).

The BPS patch checks your ROM first and refuses a wrong one. The IPS patch
does not, so check your ROM against section 5 before using it.

The ROM must be UNHEADERED (exactly 1,572,864 bytes). If yours is 1,573,376
bytes, it has a 512-byte copier header: remove it first (RomPatcher.js can
do this).

The patched ROM is expanded to 2 MB (16 Mbit). This is normal.

Save files from the Japanese version should load, but this was not tested.
Starting a new game is recommended.


-------------------------------------------------------------------------------
5. ROM INFORMATION
-------------------------------------------------------------------------------
Original ROM (file name and hashes of the dump the patch was built from):
  Nage Libre - Seijaku no Suishin (Japan).sfc
  Size:   1,572,864 bytes (no header)
  CRC32:  A98F24E1
  MD5:    cbbc7c92b5c2557cc610d58efcc50cde
  SHA-1:  25a013e43989870f4f3e59ff4e4c34bda7bc5c44

Patched ROM:
  Size:   2,097,152 bytes
  CRC32:  7EC43626
  MD5:    88a05deba9461a0e7d4744998088b51c
  SHA-1:  3ab51f96085aff3d84d693da59eb79c11a512726


-------------------------------------------------------------------------------
6. KNOWN ISSUES AND CHOICES
-------------------------------------------------------------------------------
  - Tested in the Mesen 2 emulator. Not yet tested on real hardware or a
    flash cart (FXPak/SD2SNES, etc.), or in other emulators. Reports welcome.

  - Some menus have very little room, so a few words are shortened:
    "B.stone" (birthstone), "M.stone" (moonstone), "Aqua" (aquamarine),
    "Lapis" (lapis lazuli), and "St2" for "Stage 2" on the save screen.

  - The font has no accented letters ("cliche", not "cliché").

  - A few rarely seen lines (optional events and some Extra Stage text) were
    proofread but not seen in the game.

  - Not a bug: if you play a CHG (card swap) card without having bought any
    spare cards, the card list is empty. The Japanese game does the same.


-------------------------------------------------------------------------------
7. REPORTING MISTAKES
-------------------------------------------------------------------------------
Please open an issue on GitHub:
  https://github.com/ACR-GD/nage-libre/issues

A screenshot helps a lot. If you can, say roughly where you were in the game
(stage number, or what just happened).


-------------------------------------------------------------------------------
8. CREDITS
-------------------------------------------------------------------------------
  Translation, hacking, proofreading, testing ... ACR-GD
  AI assistance (text decoding, tools, draft) .. Claude (Anthropic)

  Original game ................................. Varie, 1995

  Tools: Mesen 2 (emulation and debugging), Python.


-------------------------------------------------------------------------------
9. DISCLAIMER
-------------------------------------------------------------------------------
This is an unofficial fan translation, made for free, with no connection to
Varie or any rights holder. No ROM is included or will be provided: please
use a copy of the game you own. Do not sell this patch or ROMs patched with
it.

Version history
  v1.0 (2026-11-04)  First public release.
