--[[
  Nage Libre — trace MENU DE COMBAT v2 (Mesen2)
  But : trouver la ROUTINE + la SOURCE qui composent le menu de commandes.

  Ce qu'on sait (dumps VRAM/WRAM analysés) :
    - Le menu est sur BG3 (tilemap VRAM mot $7C00). La tilemap est d'abord
      ASSEMBLÉE dans un buffer shadow WRAM $7E:4000+ (les lignes du menu y sont
      à $7E:406E+), puis DMA'd en VRAM.
    - Les glyphes des commandes (待機/攻撃/…) sont des tuiles de POLICE COMBAT
      assemblées dans un buffer shadow WRAM $7E:2000+ (tuile N à $7E:2000+N*16).
      Les commandes occupent les tuiles ~$90..$E4. Ces glyphes sont COPIÉS depuis
      la police kanji principale (ROM) — il existe donc une LISTE source (IDs /
      offsets) qui pilote la copie. C'est cette liste qu'on cherche.

  Méthode :
    - On suit le PC courant via un callback exec (emu.getState() ne marche pas
      dans un callback d'écriture sur ce Mesen2).
    - On logue les écritures CPU dans :
        * le buffer de police   $7E:2100..$7E:2E50  (tuiles $90..$E4)
        * le shadow tilemap BG3 $7E:4040..$7E:4280  (lignes du menu)
      avec le PC, A/X/Y/DP/DB. Le pointeur source apparaît dans X ou Y.

  Usage :
    1. Charger nl-full-en.sfc, entrer en combat, AVANT d'ouvrir le menu COMMAND.
    2. Script Window → Load → ce fichier → Run.
    3. Ouvrir le menu de commandes.
    4. M'envoyer  mesen_dumps/battle_menu_trace.log

  Note perf : le suivi du PC instrumente chaque instruction → l'émulation peut
  ralentir. C'est normal ; il suffit d'ouvrir le menu une fois.
]]

local LOG_PATH = "/Users/acr/Develop/nage-libre/mesen_dumps/battle_menu_trace.log"
local MAX_LINES = 6000

local CB  = emu.callbackType or emu.memCallbackType

-- Plages WRAM (adresses bus CPU 24 bits) à surveiller en écriture.
local WATCH = {
  {0x7E2100, 0x7E2E50, "FONT"},   -- buffer police combat, tuiles $90..$E4
  {0x7E4040, 0x7E4280, "MAP"},    -- shadow tilemap BG3, fenêtre du menu
}

local fileHandle = io.open(LOG_PATH, "w")
local lineCount = 0
local curPC = 0          -- mis à jour à chaque instruction (léger)
local frame = 0

local function logline(s)
  if fileHandle then fileHandle:write(s.."\n"); fileHandle:flush() end
  if emu.log then emu.log(s) end
end

local function stop()
  lineCount = lineCount + 1
  if lineCount >= MAX_LINES and fileHandle then
    logline(string.format("=== MAX_LINES (%d) — arrêt ===", MAX_LINES))
    fileHandle:close(); fileHandle = nil
  end
end

-- Suivi du PC : exec sur tout l'espace. ON NE FAIT QUE mémoriser l'adresse
-- (pas de emu.getState() ici sinon l'émulation rame énormément).
local function onExec(addr)
  curPC = addr
end

local function mkWriteCb(tag)
  return function(addr, value)
    if fileHandle == nil then return end
    -- emu.getState() peut renvoyer un état vide dans un write cb sur ce Mesen2 ;
    -- on tente quand même pour récupérer X/Y (= pointeur source) si possible.
    local x, y, a = -1, -1, -1
    local st = emu.getState()
    if st and st.cpu then a = st.cpu.a or -1; x = st.cpu.x or -1; y = st.cpu.y or -1 end
    logline(string.format(
      "%s w $%06X = $%02X   PC=$%06X A=%04X X=%04X Y=%04X f=%d",
      tag, addr, value & 0xFF, curPC, a & 0xFFFF, x & 0xFFFF, y & 0xFFFF, frame))
    stop()
  end
end

local function onFrame() frame = frame + 1 end

logline("=== Nage Libre — trace MENU DE COMBAT v2 ===")
logline("Log: "..LOG_PATH)

-- exec global pour capturer le PC (emu.getState marche ici, pas dans un write cb)
emu.addMemoryCallback(onExec, CB.exec, 0x000000, 0xFFFFFF)

for _, w in ipairs(WATCH) do
  emu.addMemoryCallback(mkWriteCb(w[3]), CB.write, w[1], w[2])
  logline(string.format("  watch write %s  $%06X..$%06X", w[3], w[1], w[2]))
end
emu.addEventCallback(onFrame, emu.eventType.startFrame)

logline("Actif. Ouvrir le menu COMMAND, puis m'envoyer le log.")
