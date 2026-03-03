import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import get_cmap
from matplotlib.lines import Line2D

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
    prepare_groupwise_values_dict,
    prepare_hierarchy_info,
)
from utils.stats import (
    get_descriptive_stats,
    metric_to_label,
)


def ordered_unique(values):
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "linegraph", test_mode=test_mode)

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
secondary_grouping = dict(cfg["secondary_grouping"])
value_column = cfg["value_column"]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg["specified_parent"]
parent_hierarchy_level = cfg["parent_hierarchy_level"]
region_list = cfg["region_list"]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
x_axis_title = cfg["x_axis_title"]
use_region_colors = cfg["use_region_colors"]
id_system = cfg["id_system"]
error_metric = cfg["error_metric"]
secondary_group_label = cfg["secondary_group_label"]
split_line_styles = cfg["split_line_styles"]
split_markers = cfg["split_markers"]

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
x_groups = ordered_unique(grouping.values())
sample_ids = list(ids_to_files_dict.keys())
value_name = metric_to_label(value_column)

id_mapping, color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

if secondary_grouping:
    missing_secondary = [sample_id for sample_id in sample_ids if sample_id not in secondary_grouping]
    if missing_secondary:
        raise RuntimeError(
            "secondary_grouping is missing sample IDs:\n" + "\n".join(missing_secondary)
        )
    split_groups = ordered_unique(secondary_grouping[sample_id] for sample_id in sample_ids)
    combined_grouping = {
        sample_id: f"{grouping[sample_id]}|||{secondary_grouping[sample_id]}"
        for sample_id in sample_ids
    }
else:
    split_groups = []
    combined_grouping = grouping

if id_system == "KimLab16bit":
    all_individual_values = prepare_groupwise_values_dict(
        ids_to_files_dict,
        combined_grouping,
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
        combined_grouping,
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

avg_values_to_group_dict, error_to_region_group_dict, _n_to_group_dict = get_descriptive_stats(
    all_individual_values,
    error_metric=error_metric,
)

plt.figure(figsize=(12, 8))
x_positions = np.arange(len(x_groups))

if not use_region_colors:
    cmap = get_cmap("tab10")
    contrasting_colors = [cmap(i % 10) for i in range(len(avg_values_to_group_dict.keys()))]
else:
    contrasting_colors = [
        f"#{color_mapping[region]}" if not str(color_mapping[region]).startswith("#") else color_mapping[region]
        for region in avg_values_to_group_dict.keys()
    ]

for i, region_id in enumerate(avg_values_to_group_dict.keys()):
    if split_groups:
        for j, split_group in enumerate(split_groups):
            combined_keys = [f"{x_group}|||{split_group}" for x_group in x_groups]
            avg_values = np.array(
                [avg_values_to_group_dict[region_id].get(key, np.nan) for key in combined_keys],
                dtype=float,
            )
            error_values = np.array(
                [error_to_region_group_dict.get(region_id, {}).get(key, np.nan) for key in combined_keys],
                dtype=float,
            )

            valid = ~np.isnan(avg_values)
            if not np.any(valid):
                continue

            upper_bound = avg_values + np.nan_to_num(error_values, nan=0.0)
            lower_bound = avg_values - np.nan_to_num(error_values, nan=0.0)

            plt.plot(
                x_positions[valid],
                avg_values[valid],
                marker=split_markers[j % len(split_markers)],
                linestyle=split_line_styles[j % len(split_line_styles)],
                color=contrasting_colors[i],
                label="_nolegend_",
                alpha=1.0,
            )
            plt.fill_between(
                x_positions[valid],
                lower_bound[valid],
                upper_bound[valid],
                color=contrasting_colors[i],
                alpha=0.14,
            )
    else:
        avg_values = np.array(
            [avg_values_to_group_dict[region_id].get(group, np.nan) for group in x_groups],
            dtype=float,
        )
        error_values = np.array(
            [error_to_region_group_dict.get(region_id, {}).get(group, np.nan) for group in x_groups],
            dtype=float,
        )

        valid = ~np.isnan(avg_values)
        if not np.any(valid):
            continue

        upper_bound = avg_values + np.nan_to_num(error_values, nan=0.0)
        lower_bound = avg_values - np.nan_to_num(error_values, nan=0.0)

        plt.plot(
            x_positions[valid],
            avg_values[valid],
            marker="o",
            linestyle="-",
            color=contrasting_colors[i],
            label="_nolegend_",
            alpha=1.0,
        )
        plt.fill_between(
            x_positions[valid],
            lower_bound[valid],
            upper_bound[valid],
            color=contrasting_colors[i],
            alpha=0.2,
        )

plt.xlabel(x_axis_title)
plt.ylabel(value_name)
plt.title(plot_title)
plt.grid(True)
plt.xticks(x_positions, x_groups, rotation=45)

region_handles = []
for i, region_id in enumerate(avg_values_to_group_dict.keys()):
    region_name = id_mapping.get(region_id, region_id)
    region_handles.append(
        Line2D([0], [0], color=contrasting_colors[i], linestyle="-", marker="o", lw=2, label=region_name)
    )

ax = plt.gca()
fig = plt.gcf()
region_legend = ax.legend(
    handles=region_handles,
    title="Regions",
    loc="upper left",
    bbox_to_anchor=(0.0, 1.0),
    borderaxespad=0.5,
)
ax.add_artist(region_legend)

if split_groups:
    reference_color = contrasting_colors[0] if len(contrasting_colors) > 0 else "black"
    split_handles = []
    for j, split_group in enumerate(split_groups):
        split_handles.append(
            Line2D(
                [0],
                [0],
                color=reference_color,
                linestyle=split_line_styles[j % len(split_line_styles)],
                marker=split_markers[j % len(split_markers)],
                lw=2,
                label=f"{split_group}",
            )
        )
    fig.canvas.draw()
    bbox_disp = region_legend.get_window_extent(fig.canvas.get_renderer())
    bbox_axes = bbox_disp.transformed(ax.transAxes.inverted())
    second_x = min(max(bbox_axes.x1 + 0.02, 0.0), 0.98)

    ax.legend(
        handles=split_handles,
        title=secondary_group_label,
        loc="upper left",
        bbox_to_anchor=(second_x, 1.0),
        borderaxespad=0.5,
        handlelength=3.0,
    )

plt.savefig(str(save_path))
plt.show()
