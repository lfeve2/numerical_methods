from pathlib import Path
import os
import re
import subprocess

import matplotlib.pyplot as plt
import numpy as np

# Configuration du style graphique
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 9,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.autolayout": True,
    "lines.linewidth": 2.0,
})

PROJECT_ROOT = Path(__file__).resolve().parents[1]
C_SRC = Path("code") / "level2_thermal.c"
EXEC = Path("output") / "level2_thermal"
C_SRC_ABSOLUTE = PROJECT_ROOT / C_SRC
EXEC_ABSOLUTE = PROJECT_ROOT / EXEC
BASE_OUTDIR = PROJECT_ROOT / "output" / "doe_lvl2"
LOG_DIR = PROJECT_ROOT / "output" / "doe_lvl2_logs"
PLOTS_DIR = PROJECT_ROOT / "plots"

# Fichiers de sortie : l'arborescence est maintenant propre et portable sur macOS.
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
EXEC.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
BASE_OUTDIR.mkdir(parents=True, exist_ok=True)

# Plan d'expérience complet (Niveaux 1 et 2)
EXPERIMENTS = [
    {"name": "Bo_0.25", "Ga": 50.0, "Bo": 0.25, "Pr": 1.0, "level": 9},
    {"name": "Bo_0.5",  "Ga": 50.0, "Bo": 0.5,  "Pr": 1.0, "level": 9},
    {"name": "Bo_1.0",  "Ga": 50.0, "Bo": 1.0,  "Pr": 1.0, "level": 9},
    {"name": "Bo_2.0",  "Ga": 50.0, "Bo": 2.0,  "Pr": 1.0, "level": 9},
    {"name": "Bo_4.0",  "Ga": 50.0, "Bo": 4.0,  "Pr": 1.0, "level": 9},
    {"name": "Bo_6.0",  "Ga": 50.0, "Bo": 6.0,  "Pr": 1.0, "level": 9},
    {"name": "Bo_8.0",  "Ga": 50.0, "Bo": 8.0,  "Pr": 1.0, "level": 9},
    {"name": "Bo_12.0", "Ga": 50.0, "Bo": 12.0, "Pr": 1.0, "level": 9},
    {"name": "Bo_16.0", "Ga": 50.0, "Bo": 16.0, "Pr": 1.0, "level": 9},
    {"name": "Bo_20.0", "Ga": 50.0, "Bo": 20.0, "Pr": 1.0, "level": 9},
    {"name": "Bo_25.0", "Ga": 50.0, "Bo": 25.0, "Pr": 1.0, "level": 9},
    {"name": "Pr_0.2",  "Ga": 50.0, "Bo": 4.0,  "Pr": 0.2, "level": 9},
    {"name": "Pr_0.5",  "Ga": 50.0, "Bo": 4.0,  "Pr": 0.5, "level": 9},
    {"name": "Pr_2.5",  "Ga": 50.0, "Bo": 4.0,  "Pr": 2.5, "level": 9},
    {"name": "Pr_5.0",  "Ga": 50.0, "Bo": 4.0,  "Pr": 5.0, "level": 9},
]

if not C_SRC_ABSOLUTE.exists():
    raise FileNotFoundError(f"Le fichier Basilisk n'a pas été trouvé : {C_SRC_ABSOLUTE}")

print("--- Compilation Level 2 Basilisk Solver ---")
compile_proc = subprocess.run(
    ["qcc", "-O2", "-Wall", "-disable-dimensions", str(C_SRC), "-o", str(EXEC), "-lm"],
    capture_output=True,
    text=True,
    cwd=PROJECT_ROOT,
)
if compile_proc.returncode != 0:
    print("[ERROR] Compilation failed:\n", compile_proc.stderr)
    raise SystemExit(1)

results = {}
pattern = re.compile(
    r"t=\s*([\d\.\+\-eE]+)\s*\|\s*Aire=\s*([\d\.\+\-eE]+)\s*\|\s*Pos_y=\s*([\d\.\+\-eE]+)\s*\|\s*Vel_y=\s*([\d\.\+\-eE]+)\s*\|\s*Re=\s*([\d\.\+\-eE]+)\s*\|\s*Chi=\s*([\d\.\+\-eE]+)\s*\|\s*T_b=\s*([\d\.\+\-eE]+)\s*\|\s*Pe=\s*([\d\.\+\-eE]+)\s*\|\s*Nu=\s*([\d\.\+\-eE]+)\s*\|\s*Vort=\s*([\d\.\+\-eE]+)"
)

for exp in EXPERIMENTS:
    name = exp["name"]
    ga, bo, pr, lvl = exp["Ga"], exp["Bo"], exp["Pr"], exp["level"]
    case_vtu_dir = BASE_OUTDIR / name
    case_vtu_dir.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{name}.log"

    print(f"\n>>> Running: {name:<8} (Ga={ga}, Bo={bo}, Pr={pr}, Level={lvl})...")
    with open(log_file, "w") as fp:
        subprocess.run(
            [str(EXEC_ABSOLUTE), str(lvl), str(ga), str(bo), str(pr), name],
            stderr=fp,
            check=True,
            cwd=PROJECT_ROOT,
        )

    t_l, v_l, chi_l, tb_l, nu_l = [], [], [], [], []
    with open(log_file, "r") as fp:
        for line in fp:
            m = pattern.search(line)
            if m:
                t, _, _, v, _, chi, tb, _, nu, _ = map(float, m.groups())
                t_l.append(t)
                v_l.append(v)
                chi_l.append(chi)
                tb_l.append(tb)
                nu_l.append(nu)

    results[name] = {
        "Ga": ga, "Bo": bo, "Pr": pr,
        "t": np.array(t_l), "v": np.array(v_l),
        "Chi": np.array(chi_l), "Tb": np.array(tb_l), "Nu": np.array(nu_l),
    }

plt.figure(figsize=(6, 4.5))
for name in ["Bo_0.25", "Bo_0.5", "Bo_4.0", "Bo_20.0"]:
    d = results[name]
    mask = d["t"] <= 17.0
    plt.plot(d["t"][mask], d["v"][mask], label=name)
plt.xlabel(r"Dimensionless time $t^* = t\sqrt{g/D}$")
plt.ylabel(r"Rise velocity $v_y^*$")
plt.title("Terminal Velocity Dynamics")
plt.xlim(0, 17.0)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(PLOTS_DIR / "lvl1_velocity.png", dpi=300)
plt.close()
print("[OK] Saved 'lvl1_velocity.png'")

bo_cases = [e["name"] for e in EXPERIMENTS if e["name"].startswith("Bo_")]
bo_vals = []
chi_vals = []

for c in bo_cases:
    d = results[c]
    mask = (d["t"] >= 8.0) & (d["t"] <= 14.0)
    bo_vals.append(results[c]["Bo"])
    chi_vals.append(float(np.median(d["Chi"][mask])))

plt.figure(figsize=(6, 4.5))
plt.plot(bo_vals, chi_vals, "o", color="darkblue", markersize=7, label="Basilisk (Moments 2D)")
bo_model = np.linspace(0.2, 26.0, 200)
plt.plot(bo_model, 1.0 + 0.163 * (bo_model ** 0.757), "--", color="red", label="Wellek et al. (1966) - 3D")
plt.xlabel(r"Bond number $Bo = \rho_l g D^2 / \sigma$")
plt.ylabel(r"Equilibrium aspect ratio $\chi = \sqrt{M_{xx}/M_{yy}}$")
plt.title(r"Bubble Flattening Law ($Ga = 50$)")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(PLOTS_DIR / "lvl1_aspect_ratio.png", dpi=300)
plt.close()
print("[OK] Saved 'lvl1_aspect_ratio.png'")

plt.figure(figsize=(6, 4.5))
for name in ["Pr_0.2", "Bo_4.0", "Pr_5.0"]:
    d = results[name]
    mask = d["t"] <= 17.0
    lbl = f"Pr = {results[name]['Pr']}"
    plt.plot(d["t"][mask], d["Tb"][mask], label=lbl)
plt.xlabel(r"Dimensionless time $t^* = t\sqrt{g/D}$")
plt.ylabel(r"Core temperature $\langle T_b \rangle$")
plt.title("Cooling Kinetics of the Hot Bubble")
plt.xlim(0, 17.0)
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(PLOTS_DIR / "lvl2_cooling.png", dpi=300)
plt.close()
print("[OK] Saved 'lvl2_cooling.png'")

pr_cases = ["Pr_0.2", "Pr_0.5", "Bo_4.0", "Pr_2.5", "Pr_5.0"]
pr_vals = [results[c]["Pr"] for c in pr_cases]
tb_finals = []

for c in pr_cases:
    d = results[c]
    idx = np.argmin(np.abs(d["t"] - 17.0))
    tb_finals.append(d["Tb"][idx])

plt.figure(figsize=(6, 4.5))
plt.plot(pr_vals, tb_finals, "s-", color="crimson", markersize=7)
plt.xscale("log")
plt.xlabel(r"Prandtl number $Pr = \nu_l / \alpha_l$ (log scale)")
plt.ylabel(r"Core temperature $\langle T_b \rangle$ at $t^* = 17$")
plt.title(r"Boundary Layer Insulation ($\delta_T \propto Pr^{-1/2}$)")
plt.grid(True, which="both", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig(PLOTS_DIR / "lvl2_boundary_layer.png", dpi=300)
plt.close()
print("[OK] Saved 'lvl2_boundary_layer.png'")