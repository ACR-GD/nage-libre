# Réinsertion / rebuild d'une ROM SNES — checklist « sans rien oublier »

Accompagne `scripts/snes_rebuild_toolkit.py`. Ordre des opérations pour
reconstruire une ROM modifiée sans la corrompre ni oublier une étape.

## La checklist

1. **Travailler sans en-tête SMC.** Le toolkit retire automatiquement les 512 o
   du copieur (`strip_smc_header`) et peut les ré-ajouter à la sortie avec
   `--keep-smc`. Garde l'original intact (on patche une copie).
2. **Expanser AVANT d'écrire** si les nouvelles données ne tiennent pas. La ROM
   doit rester un multiple de 32 Ko (idéalement une puissance de deux).
   `--expand MBIT` agrandit ET met à jour l'octet de taille du header.
3. **Placer les données** :
   - patch en place (même taille) → `write_file` / `write_snes` ;
   - données plus grosses → `alloc()` (cherche un trou de 0x00/0xFF libre) puis
     écrire dedans. `--free-space` liste les zones disponibles.
4. **Repointer.** Si une chaîne/un asset change de taille ou d'emplacement, mettre
   à jour la table de pointeurs (`repoint`, pointeurs 2 ou 3 octets). C'est
   l'oubli classique qui fait afficher du charabia.
5. **Corriger l'octet de taille du header** (`$..D7`) — fait par `--expand`.
6. **Recalculer le CHECKSUM + complément** (`--fix-checksum`, fait aussi par
   `--expand` et le mode `--build`). C'est l'oubli n°1 : beaucoup d'émulateurs et
   tous les flashcarts/consoles réelles rejettent ou signalent une ROM au
   checksum faux. L'algo gère le miroir des tailles non puissances de deux.
7. **Vérifier** (`--verify`) : taille multiple de 32 Ko, checksum cohérent,
   complément = checksum XOR 0xFFFF, octet de taille correct, et **aucun
   chevauchement** d'écriture (deux patchs qui s'écrasent).
8. **Diffuser en patch** (`--make-ips`) plutôt que la ROM (légal + petit).

## Rebuild reproductible : le manifeste

Plutôt que d'enchaîner les commandes, décris tout dans un JSON et lance
`--build` : expansion, écritures (hex / binaire / remplissage / alloc auto),
repointages, fix header + checksum, vérification — dans l'ordre, à chaque build.

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
python3 scripts/snes_rebuild_toolkit.py jeu.sfc --build build.json -o jeu_fr.sfc
```

## Commandes principales

| Besoin | Commande |
|---|---|
| Expanser + fixer header/checksum | `--expand MBIT -o out.sfc` |
| Recalculer le checksum | `--fix-checksum -o out.sfc` |
| Lister l'espace libre | `--free-space --min 256` |
| Vérifier une ROM | `--verify` |
| Générer un patch IPS | `--make-ips modifiee.sfc -o patch.ips` |
| Appliquer un patch IPS | `--apply-ips patch.ips -o out.sfc` |
| Rebuild déclaratif complet | `--build manifest.json -o out.sfc` |

> Pour l'analyse en amont (trouver texte, tables, routines, graphismes,
> compression) voir `scripts/snes_re_toolkit.py` et
> `docs/snes_compression_id.md`.
