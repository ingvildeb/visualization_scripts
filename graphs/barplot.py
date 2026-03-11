import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import (
    load_script_config,
    normalize_user_path,
    require_absolute_path,
    require_file,
)
from utils.atlas_data_prep import (
    collect_values_by_hierarchy,
    collect_values_directly,
    create_child_to_parent_mapping,
    load_and_prepare_data,
    prepare_hierarchy_info,
)
from utils.stats import (
    average_value_dicts,
    metric_to_label,
)


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "barplot", test_mode=test_mode)

# -------------------------
# CONFIG PARAMETERS
# -------------------------
files = [
    require_file(
        require_absolute_path(normalize_user_path(p), "Input file"),
        "Input file",
    )
    for p in cfg["files"]
]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg["specified_parent"] or None
parent_hierarchy_level = cfg["parent_hierarchy_level"]
value_column = cfg["value_column"]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
id_system = cfg["id_system"]
region_list = cfg["region_list"]
error_metric = cfg.get("error_metric", "se")
error_mode = cfg.get("error_mode", "bars")
jitter_frac = cfg.get("jitter_frac", 0.0)

# -------------------------
# PATHS
# -------------------------
repo_root = script_path.parent.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}.{out_format}"
else:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}.{out_format}"

# -------------------------
# MAIN
# -------------------------
n = len(files)
value_name = metric_to_label(value_column)

id_mapping, color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, parent_hierarchy_level)

all_values = []
for file in files:
    if id_system == "KimLab16bit":
        data_file = load_and_prepare_data(file, allen2intfile, reverse=True)
    elif id_system == "OriginalAllen":
        data_file = load_and_prepare_data(file, allen2intfile, reverse=False)
    else:
        raise RuntimeError("ID system not recognized. Must be KimLab16bit or OriginalAllen")

    if region_list:
        values_in_file = collect_values_directly(data_file, value_column, region_list, id_mapping)
    else:
        values_in_file = collect_values_by_hierarchy(
            data_file,
            value_column,
            hierarchy_regions,
            selected_hierarchy,
            child_to_parent_dict,
            specified_parent,
        )

    all_values.append(values_in_file)

if n > 1:
    value_dict, error_dict = average_value_dicts(all_values, error_metric=error_metric)
else:
    value_dict, error_dict = all_values[0], None

values = []
error_values = []
region_names = []
region_colors = []
parent_labels = []

for region_id, value in value_dict.items():
    region_names.append(id_mapping.get(region_id))
    region_colors.append(f"#{color_mapping.get(region_id)}")
    parent_labels.append(child_to_parent_dict.get(region_id))
    values.append(value)

    if error_dict:
        error_values.append(error_dict.get(region_id))

for i in range(len(parent_labels) - 1):
    if parent_labels[i] == "":
        parent_labels[i] = parent_labels[i + 1]

fig, ax = plt.subplots(figsize=(35, 15))
x = np.arange(len(region_names))
bar_width = 0.8

show_error_bars = False
show_dots = False
yerr_values = None

if n > 1:
    error_mode = str(error_mode).lower()
    if error_mode not in {"bars", "dots", "both", "none"}:
        raise ValueError("error_mode must be one of: bars, dots, both, none")

    show_error_bars = error_mode in {"bars", "both"}
    show_dots = error_mode in {"dots", "both"}
    yerr_values = error_values if show_error_bars else None

ax.bar(x, values, yerr=yerr_values, color=region_colors, width=bar_width, capsize=3 if yerr_values is not None else 0)

if show_dots:
    rng = np.random.default_rng(0)
    for j, region_id in enumerate(value_dict.keys()):
        vals = []
        for d in all_values:
            if region_id in d:
                vals.append(d[region_id])
        if not vals:
            continue
        vals = np.asarray(vals, dtype=float)
        jitter = rng.normal(0, bar_width * jitter_frac, size=vals.size)
        x_points = x[j] + jitter
        ax.scatter(x_points, vals, s=25, alpha=0.85, color="black", zorder=3)

ax.set_ylabel(value_name, fontsize=16)
ax.set_title(plot_title, fontsize=20)
ax.set_xticks(x)
ax.set_xticklabels(region_names, rotation=45, ha="right", fontsize=16)

if selected_hierarchy in ["CustomLevel1_gm", "CustomLevel2_gm", "CustomLevel3_gm", "FullHierarchy"] and not specified_parent:
    ax.set_xticklabels([])
    ax.tick_params(axis="x", which="both", bottom=False, top=False)

    sec_ax = ax.secondary_xaxis("bottom")
    sec_ax.tick_params(axis="x", which="both", bottom=False, top=False)

    unique_parents = list(dict.fromkeys(parent_labels))
    group_boundaries = []
    group_positions = []
    parent_names = []

    for parent in unique_parents:
        indices = [i for i, x in enumerate(parent_labels) if x == parent]
        if indices:
            start_index, end_index = indices[0], indices[-1]
            group_boundaries.append((start_index, end_index))
            group_positions.append((start_index + end_index) / 2)

        parent_names.append(parent)

    sec_ax.set_xticks(group_positions)
    sec_ax.set_xticklabels(parent_names, rotation=45, ha="right", fontsize=16)
    plt.subplots_adjust(bottom=0.2)

    for start, end in group_boundaries:
        ax.annotate(
            "",
            xy=(start, -0.005),
            xytext=(end, -0.005),
            arrowprops=dict(arrowstyle="-", lw=2, color="black"),
            annotation_clip=False,
            xycoords=("data", "axes fraction"),
            textcoords=("data", "axes fraction"),
        )

plt.tight_layout()
plt.savefig(save_path)
plt.show()
