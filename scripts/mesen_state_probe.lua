--[[
  Sonde : découvre la structure de emu.getState() sur CETTE version de Mesen,
  pour corriger l'extraction du PC/registres dans les traces.

  Usage : Script Window → Load → Run. Le fichier est écrit immédiatement.
  M'envoyer  mesen_dumps/state_probe.txt
]]
local OUT = "/Users/acr/Develop/nage-libre/mesen_dumps/state_probe.txt"
local f = io.open(OUT, "w")
local function w(s) f:write(s.."\n") end

local function dump(t, prefix, depth)
  if depth > 4 then return end
  if type(t) ~= "table" then
    w(prefix.." = "..tostring(t).."  ("..type(t)..")")
    return
  end
  local keys = {}
  for k,_ in pairs(t) do keys[#keys+1]=tostring(k) end
  table.sort(keys)
  for _,k in ipairs(keys) do
    local v = t[k]
    if type(v) == "table" then
      w(prefix.."."..k.." : table")
      dump(v, prefix.."."..k, depth+1)
    else
      w(prefix.."."..k.." = "..tostring(v).."  ("..type(v)..")")
    end
  end
end

w("=== emu.getState() structure ===")
local ok, st = pcall(emu.getState)
if ok then
  dump(st, "state", 0)
else
  w("ERREUR emu.getState(): "..tostring(st))
end

w("\n=== enums dispo ===")
for _,name in ipairs({"callbackType","memCallbackType","memType","eventType","cpuType"}) do
  local e = emu[name]
  if type(e)=="table" then
    local ks={}; for k,_ in pairs(e) do ks[#ks+1]=tostring(k) end
    table.sort(ks)
    w("emu."..name.." : "..table.concat(ks,", "))
  else
    w("emu."..name.." = "..tostring(e))
  end
end
f:close()
if emu.log then emu.log("state_probe → "..OUT) end
