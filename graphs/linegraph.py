import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import get_cmap

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import load_script_config, normalize_user_path
from utils.utils import get_descriptive_stats, prepare_groupwise_values_dict, prepare_hierarchy_info


def resolve_config_path(path_like: str | Path, script_dir: Path) -> Path:
    p = normalize_user_path(path_like)
    return p if p.is_absolute() else (script_dir / p).resolve()


def resolve_value_name(value_column: str) -> str:
    if value_column == "cell_density":
        return "Density"
    if value_column == "cell_counted":
        return "Cell"
    if value_column == "ROI_Volume_mm_3":
        return "Region volume"
    return value_column


script_path = Path(__file__).resolve()
script_dir = script_path.parent
test_mode = False
cfg = load_script_config(script_path, "linegraph", test_mode=test_mode)

ids_to_files_dict = {k: resolve_config_path(v, script_dir) for k, v in cfg["ids_to_files"].items()}
grouping = dict(cfg["grouping"])
value_column = cfg["value_column"]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg.get("specified_parent")
if specified_parent in ("", "None", "none", False):
    specified_parent = None
parent_hierarchy_level = cfg["parent_hierarchy_level"]
region_list = cfg.get("region_list", [])
out_filename_prefix = cfg["out_filename_prefix"]
out_path = resolve_config_path(cfg["out_path"], script_dir)
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
x_axis_title = cfg["x_axis_title"]
use_region_colors = bool(cfg.get("use_region_colors", False))
id_system = cfg["id_system"]
error_metric = str(cfg.get("error_metric", "se")).lower()

repo_root = script_dir.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}.{out_format}"
else:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}.{out_format}"

groups = []
for sample_id, group in grouping.items():
    if group not in groups:
        groups.append(group)

value_name = resolve_value_name(value_column)

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

avg_values_to_group_dict, error_to_region_group_dict, _n_to_group_dict = get_descriptive_stats(
    all_individual_values,
    error_metric=error_metric,
)

plt.figure(figsize=(12, 8))

if not use_region_colors:
    cmap = get_cmap("tab10")
    contrasting_colors = [cmap(i % 10) for i in range(len(avg_values_to_group_dict.keys()))]
else:
    contrasting_colors = [
        f"#{color_mapping[region]}" if not str(color_mapping[region]).startswith("#") else color_mapping[region]
        for region in avg_values_to_group_dict.keys()
    ]

for i, region_id in enumerate(avg_values_to_group_dict.keys()):
    region_name = id_mapping.get(region_id, region_id)
    avg_values = [avg_values_to_group_dict[region_id].get(group, 0) for group in groups]
    error_values = [error_to_region_group_dict.get(region_id, {}).get(group, 0) for group in groups]

    upper_bound = np.array(avg_values) + np.array(error_values)
    lower_bound = np.array(avg_values) - np.array(error_values)

    plt.plot(groups, avg_values, marker="o", linestyle="-", color=contrasting_colors[i], label=region_name, alpha=1.0)
    plt.fill_between(groups, lower_bound, upper_bound, color=contrasting_colors[i], alpha=0.2)

plt.xlabel(x_axis_title)
plt.ylabel(value_name)
plt.title(plot_title)
plt.grid(True)
plt.xticks(rotation=45)
plt.legend(title="Regions")

plt.savefig(str(save_path))
plt.show()
