from pathlib import Path
import re
import subprocess

import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
PLOTS_DIR = PROJECT_ROOT / "plots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Mesh levels (use [7, 8, 9] for a quick run, [8, 9, 10] for final results)
LEVELS = [8, 9, 10]
WIDTH = 16.0
C_SRC = Path("code") / "level1_hydro.c"
EXEC = Path("output") / "level1_hydro"
C_SRC_ABSOLUTE = PROJECT_ROOT / C_SRC
EXEC_ABSOLUTE = PROJECT_ROOT / EXEC

if not C_SRC_ABSOLUTE.exists():
    raise FileNotFoundError(
        "No Level 1 solver was found in level1/code/. "
        "Add level1_hydro.c before running this script."
    )

print("--- Compiling the Basilisk code ---")
subprocess.run(
    ["qcc", "-O2", "-Wall", "-disable-dimensions", str(C_SRC), "-o", str(EXEC), "-lm"],
    cwd=PROJECT_ROOT,
    check=True,
)

results = {}
pattern = re.compile(
    r"t=\s*([\d\.\+\-eE]+)\s*\|\s*Aire=\s*([\d\.\+\-eE]+)\s*\|\s*Pos_y=\s*([\d\.\+\-eE]+)\s*\|\s*Vel_y=\s*([\d\.\+\-eE]+)\s*\|\s*Re=\s*([\d\.\+\-eE]+)"
)

for lvl in LEVELS:
    log_name = OUTPUT_DIR / f"log_lvl_{lvl}.txt"
    print(f"Running the simulation for LEVEL = {lvl}...")
    with open(log_name, "w") as log_file:
        subprocess.run([str(EXEC_ABSOLUTE), str(lvl)], stderr=log_file, check=True)

    t_list, s_list, y_list, v_list, re_list = [], [], [], [], []
    with open(log_name, "r") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                t, s, y, v, re_val = map(float, m.groups())
                t_list.append(t)
                s_list.append(s)
                y_list.append(y)
                v_list.append(v)
                re_list.append(re_val)

    if not t_list:
        raise RuntimeError(f"No data was extracted from {log_name}. Check the C program output.")

    results[lvl] = {
        "t": np.array(t_list),
        "s": np.array(s_list),
        "y": np.array(y_list),
        "v": np.array(v_list),
        "Re": np.array(re_list),
    }

print("\n" + "=" * 62)
print(f"{'LEVEL':^7} | {'Delta_x_min':^12} | {'Terminal velocity':^18} | {'Max area error':^15}")
print("=" * 62)

v_inf = {}
for lvl in LEVELS:
    dx = WIDTH / (2**lvl)
    data = results[lvl]

    idx_start = int(0.8 * len(data["v"]))
    v_terminal = np.mean(data["v"][idx_start:])
    v_inf[lvl] = v_terminal

    s0 = data["s"][0]
    err_s_max = np.max(np.abs(data["s"] - s0) / s0) * 100.0

    print(f"{lvl:^7d} | {dx:^12.5f} | {v_terminal:^18.5f} | {err_s_max:^14.3f}%")

print("=" * 62)

if len(LEVELS) >= 3:
    e1 = abs(v_inf[LEVELS[1]] - v_inf[LEVELS[0]])
    e2 = abs(v_inf[LEVELS[2]] - v_inf[LEVELS[1]])
    if e2 > 0 and e1 > 0:
        p = np.log(e1 / e2) / np.log(2.0)
        print(f"Apparent spatial convergence order: p ≈ {p:.2f}")

fig, axs = plt.subplots(1, 2, figsize=(12, 5))

for lvl in LEVELS:
    axs[0].plot(results[lvl]["t"], results[lvl]["v"], label=f"LEVEL {lvl}")
axs[0].set_xlabel("Temps adimensionnel $t$")
axs[0].set_ylabel("Vitesse d'ascension $v_{by}(t)$")
axs[0].set_title("Vitesse d'ascension")
axs[0].grid(True)
axs[0].legend()

for lvl in LEVELS:
    s0 = results[lvl]["s"][0]
    rel_err_s = (results[lvl]["s"] - s0) / s0 * 100.0
    axs[1].plot(results[lvl]["t"], rel_err_s, label=f"LEVEL {lvl}")
axs[1].set_xlabel("Temps adimensionnel $t$")
axs[1].set_ylabel("Relative area error $\\Delta S / S_0$ (%)")
axs[1].set_title("Mass conservation (VOF)")
axs[1].grid(True)
axs[1].legend()

plt.tight_layout()
plt.savefig(PLOTS_DIR / "convergence_study.pdf")
print("\nPlot saved as 'convergence_study.pdf'.")