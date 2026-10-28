from pathlib import Path
import re
import subprocess

import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_ROOT / "output" / "doe_lvl3_logs"
PLOTS_DIR = PROJECT_ROOT / "plots"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

LEVEL = 9
BO = 4.0
PR = 1.0
COLLAPSE_THRESHOLD = 0.05

SWEEP_JAKOB = [
    {"name": f"Ja_{ja:.1f}", "Ga": 50.0, "Ja": ja}
    for ja in (0.2, 0.4, 0.6, 0.8)
]
SWEEP_GALILEI = [
    {"name": f"Ga_{ga:.0f}", "Ga": ga, "Ja": 0.6}
    for ga in (10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0)
]

LINE_PATTERN = re.compile(
    r"t=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Aire=\s*([\d.+\-eE]+)\s*\|\s*"
    r"V_rat=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Pos_y=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Vel_y=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Re=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Chi=\s*([\d.+\-eE]+)\s*\|\s*"
    r"T_b=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Pe=\s*([\d.+\-eE]+)\s*\|\s*"
    r"Nu=\s*([\d.+\-eE]+)"
)


def compile_solver() -> None:
    """Compile the Level 3 Basilisk solver from its project directory."""
    subprocess.run(
        [
            "qcc",
            "-O2",
            "-Wall",
            "-disable-dimensions",
            "level3_phase_change.c",
            "-o",
            "level3_phase_change",
            "-lm",
        ],
        cwd=PROJECT_ROOT / "code",
        check=True,
    )


def parse_log(log_path: Path) -> dict[str, np.ndarray]:
    values = [[] for _ in range(10)]
    with log_path.open() as log_file:
        for line in log_file:
            match = LINE_PATTERN.search(line)
            if match:
                for index, value in enumerate(match.groups()):
                    values[index].append(float(value))

    if not values[0]:
        raise RuntimeError(f"No simulation data was found in {log_path}.")

    return {
        "t": np.asarray(values[0]),
        "V_rat": np.asarray(values[2]),
        "Vel_y": np.asarray(values[4]),
        "Pe": np.asarray(values[8]),
    }


def run_case(case: dict[str, float | str]) -> dict[str, np.ndarray]:
    name = str(case["name"])
    log_path = LOG_DIR / f"{name}.log"
    command = [
        "./code/level3_phase_change",
        str(LEVEL),
        str(case["Ga"]),
        str(BO),
        str(PR),
        str(case["Ja"]),
        name,
    ]

    print(
        f"Running {name}: LEVEL={LEVEL}, Ga={case['Ga']}, "
        f"Bo={BO}, Pr={PR}, Ja={case['Ja']}"
    )
    with log_path.open("w") as log_file:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            stderr=log_file,
            check=True,
        )

    data = parse_log(log_path)
    data["R_norm"] = np.sqrt(np.maximum(data["V_rat"], 0.0))
    return data


def collapse_time_and_mean_pe(data: dict[str, np.ndarray]) -> tuple[float, float]:
    collapse_indices = np.flatnonzero(data["V_rat"] < COLLAPSE_THRESHOLD)
    if collapse_indices.size == 0:
        raise RuntimeError(
            f"No collapse threshold crossing found for V_rat < "
            f"{COLLAPSE_THRESHOLD}."
        )

    collapse_index = int(collapse_indices[0])
    lifetime_slice = slice(0, collapse_index + 1)
    collapse_time = float(data["t"][collapse_index])
    mean_pe = float(np.mean(data["Pe"][lifetime_slice]))
    return collapse_time, mean_pe


def plot_results(
    jakob_results: dict[str, dict[str, np.ndarray]],
    galilei_results: dict[str, dict[str, np.ndarray]],
) -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.labelsize": 12,
            "axes.titlesize": 13,
            "legend.fontsize": 9,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.autolayout": True,
            "lines.linewidth": 2.0,
        }
    )

    fig, axis = plt.subplots(figsize=(7, 5))
    for name, data in jakob_results.items():
        axis.plot(data["t"], data["R_norm"], label=name)
    axis.set_xlabel(r"Dimensionless time $t$")
    axis.set_ylabel(r"Normalized radius $R(t)/R_0$")
    axis.set_title("Radius history: Jakob-number sweep")
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend()
    fig.savefig(PLOTS_DIR / "level3_radius_history.png", dpi=300)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 5))
    for name, data in jakob_results.items():
        axis.plot(data["t"], data["Vel_y"], label=name)
    axis.set_xlabel(r"Dimensionless time $t$")
    axis.set_ylabel(r"Vertical velocity $V_y$")
    axis.set_title("Bubble deceleration")
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend()
    fig.savefig(PLOTS_DIR / "level3_bubble_deceleration.png", dpi=300)
    plt.close(fig)

    collapse_times = []
    mean_pes = []
    labels = []
    for name, data in galilei_results.items():
        collapse_time, mean_pe = collapse_time_and_mean_pe(data)
        collapse_times.append(collapse_time)
        mean_pes.append(mean_pe)
        labels.append(name)

    mean_pes_array = np.asarray(mean_pes)
    collapse_times_array = np.asarray(collapse_times)
    fig, axis = plt.subplots(figsize=(7, 5))
    axis.loglog(
        mean_pes_array,
        collapse_times_array,
        "o-",
        label="Simulation",
    )

    reference_factor = collapse_times_array[0] * np.sqrt(mean_pes_array[0])
    reference_pe = np.geomspace(mean_pes_array.min(), mean_pes_array.max(), 100)
    axis.loglog(
        reference_pe,
        reference_factor * reference_pe ** -0.5,
        "--",
        label=r"Reference: $t_{\mathrm{collapse}}\propto Pe^{-1/2}$",
    )
    for pe, time, label in zip(mean_pes_array, collapse_times_array, labels):
        axis.annotate(label, (pe, time), xytext=(5, 5), textcoords="offset points")
    axis.set_xlabel(r"Mean Péclet number $\overline{Pe}$")
    axis.set_ylabel(r"Collapse time $t_{\mathrm{collapse}}$")
    axis.set_title("Convective collapse lifetime")
    axis.grid(True, which="both", linestyle="--", alpha=0.6)
    axis.legend()
    fig.savefig(PLOTS_DIR / "level3_convective_lifetime.png", dpi=300)
    plt.close(fig)
    print(f"Saved plot to {PLOTS_DIR / 'level3_radius_history.png'}")
    print(f"Saved plot to {PLOTS_DIR / 'level3_bubble_deceleration.png'}")
    print(f"Saved plot to {PLOTS_DIR / 'level3_convective_lifetime.png'}")


def main() -> None:
    print("--- Compiling the Level 3 Basilisk solver ---")
    compile_solver()

    jakob_results = {
        str(case["name"]): run_case(case) for case in SWEEP_JAKOB
    }
    galilei_results = {
        str(case["name"]): run_case(case) for case in SWEEP_GALILEI
    }
    plot_results(jakob_results, galilei_results)


if __name__ == "__main__":
    main()
