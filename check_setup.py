"""Quick diagnostic: verify PRICING_BASE_DIR and that input files exist."""
import sys
from pathlib import Path

import config

I_FILES = [
    "I35_MSAttributeValueLevel_1", "I38_ModalityBasePrice_1",
    "I37_OSAttributeValueLevel_1", "I51_OptionalServiceAttributeValue_1",
    "I36_SPAttributeValueLevel_1", "I52_StrategicPartAttributeValue_1",
    "I53_MaintenanceServiceAttributeValue_1", "I62_CommercialSystem_1",
    "I32_CommercialViewGroupLocal_1",
]
B_FILES = [
    "B53_MaintenanceServiceAttributeValue_1", "B52_StrategicPartAttributeValue_1",
    "B49_CommercialSystem_1", "B32_System_1",
]

server = sys.argv[1] if len(sys.argv) > 1 else "HOS"
print(f"PRICING_BASE_DIR resolved to: {config.BASE_DIR}")
print(f"Exists: {config.BASE_DIR.exists()}\n")

paths = config.server_paths(server)
ok = True
for folder, stems in (("i_files", I_FILES), ("b_files", B_FILES)):
    d = paths[folder]
    print(f"[{folder}] {d}  ({'OK' if d.is_dir() else 'MISSING FOLDER'})")
    for stem in stems:
        f = d / f"{stem}_{server}_PROD.xlsx"
        present = f.exists()
        ok = ok and present
        print(f"   {'[ok]' if present else '[--]'} {f.name}")
    print()

print("All inputs present." if ok else "Some inputs are missing (see [--] above).")
