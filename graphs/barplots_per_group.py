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
from utils.utils import (
    get_descriptive_stats,
    metric_to_label,
    perform_t_tests,
    prepare_groupwise_values_dict,
    prepare_hierarchy_info,
)


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "barplots_per_group", test_mode=test_mode)

# -------------------------
# CONFIG PARAMETERS
# -------------------------
ids_to_files_dict = {
    k: require_file(
        require_absolute_path(normalize_user_path(v), f"Input file for {k}"),
        f"Input file for {k}",
    )
    for k, v in cfg["ids_to_files"].items()
}
grouping = dict(cfg["grouping"])
value_column = cfg["value_column"]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg["specified_parent"]
parent_hierarchy_level = cfg["parent_hierarchy_level"]
region_list = cfg["region_list"]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
apply_t_test = cfg["apply_t_test"]
hatch_patterns = cfg["hatch_patterns"]
id_system = cfg["id_system"]
error_metric = cfg["error_metric"]
error_mode = cfg["error_mode"]
jitter_frac = cfg["jitter_frac"]

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
groups = list(dict.fromkeys(grouping.values()))
value_name = metric_to_label(value_column)

id_mapping, color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

if id_system == "KimLab16bit":
    all_individual_values = prepare_groupwise_values_dict(
        ids_to_files_dict,
        grouping,
        value_column,
        allen2intfile,
        selected_hierarchy,
        specified_parent,
        hierarchy_regions,
        custom_hier_path,
        parent_hierarchy_level,
        id_mapping,
        region_list,
        reverse=True,
    )
elif id_system == "OriginalAllen":
    all_individual_values = prepare_groupwise_values_dict(
        ids_to_files_dict,
        grouping,
        value_column,
        allen2intfile,
        selected_hierarchy,
        specified_parent,
        hierarchy_regions,
        custom_hier_path,
        parent_hierarchy_level,
        id_mapping,
        region_list,
        reverse=False,
    )
else:
    raise RuntimeError("ID system not recognized. Must be KimLab16bit or OriginalAllen")

avg_values_to_region_dict, error_to_region_group_dict, n_to_group_dict = get_descriptive_stats(
    all_individual_values,
    error_metric=error_metric,
)

if apply_t_test and len(groups) > 2:
    print(f"Not able to apply t-test for n = {len(groups)} groups. Consider another statistical test.")
    apply_t_test = False

significant_results = {region: None for region in avg_values_to_region_dict.keys()}
if apply_t_test:
    significant_results = perform_t_tests(all_individual_values, groups[0], groups[1])

region_names = list(avg_values_to_region_dict.keys())
region_name_map = {region: id_mapping[region] for region in region_names}
region_colors = [f"#{color_mapping.get(region)}" for region in region_names]

num_groups = len(groups)
error_mode = str(error_mode).lower()
if error_mode not in {"bars", "dots", "both", "none"}:
    raise ValueError("error_mode must be one of: bars, dots, both, none")

show_error_bars = error_mode in {"bars", "both"}
show_dots = error_mode in {"dots", "both"}

extra_groups = num_groups - 2
x = np.arange(len(region_names))
width = 0.4 - (extra_groups * 0.15)
width = max(width, 0.08)
group_space = 0.1
fig_width = 12 + (extra_groups + 8)

fig, ax = plt.subplots(figsize=(fig_width, 7))
rng = np.random.default_rng(0)

for i, group in enumerate(groups):
    bar_positions = x + i * (width + group_space)
    bar_values = [avg_values_to_region_dict.get(region, {}).get(group, 0) for region in region_names]
    y_errors = [error_to_region_group_dict.get(region, {}).get(group, 0) for region in region_names]

    hatch = hatch_patterns[i % len(hatch_patterns)]
    ax.bar(
        bar_positions,
        bar_values,
        width,
        yerr=y_errors if show_error_bars else None,
        capsize=3 if show_error_bars else 0,
        label=f"{group}, n = {n_to_group_dict.get(group)}",
        color=region_colors,
        hatch=hatch,
        zorder=1,
    )

    if show_dots and isinstance(all_individual_values, dict):
        for j, region in enumerate(region_names):
            vals = all_individual_values.get(region, {}).get(group, None)
            if vals is None:
                continue
            vals = np.asarray(vals, dtype=float)
            if vals.size == 0:
                continue
            jitter = rng.normal(0, width * jitter_frac, size=vals.size)
            x_points = bar_positions[j] + jitter
            ax.scatter(x_points, vals, s=25, alpha=0.85, color="black", zorder=3)

for j, region in enumerate(region_names):
    if region in significant_results and significant_results[region] is not None:
        start_x = j - (width + group_space) * 0.1
        end_x = j + (width + group_space)

        candidates = []
        for g in groups:
            candidates.append(avg_values_to_region_dict.get(region, {}).get(g, 0))
            if show_dots and isinstance(all_individual_values, dict):
                vals = all_individual_values.get(region, {}).get(g, [])
                if len(vals) > 0:
                    candidates.append(np.max(vals))
            if show_error_bars:
                candidates.append(
                    avg_values_to_region_dict.get(region, {}).get(g, 0) +
                    error_to_region_group_dict.get(region, {}).get(g, 0)
                )

        max_val = max(candidates) if candidates else 0
        y_bracket = max_val + 0.08 * (max_val if max_val != 0 else 1)

        ax.plot([start_x, end_x], [y_bracket, y_bracket], color="black", lw=1.5, zorder=4)
        ax.annotate(
            significant_results[region],
            xy=((start_x + end_x) / 2, y_bracket + 0.03 * (max_val if max_val != 0 else 1)),
            fontsize=12,
            ha="center",
        )

ax.set_xlabel("Regions")
ax.set_ylabel(value_name)
ax.set_title(plot_title)
ax.set_xticks(x + (num_groups - 1) * (width + group_space) / 2)
ax.set_xticklabels([region_name_map.get(region) for region in region_names], rotation=45, ha="right")
ax.legend()

plt.tight_layout()
plt.savefig(save_path)
plt.show()
