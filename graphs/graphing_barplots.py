import sys
from pathlib import Path

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
    average_value_dicts,
    collect_values_by_hierarchy,
    collect_values_directly,
    create_barplot,
    create_child_to_parent_mapping,
    load_and_prepare_data,
    metric_to_label,
    prepare_hierarchy_info,
)


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "graphing_barplots", test_mode=test_mode)

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
specified_parent = cfg["specified_parent"]
parent_hierarchy_level = cfg["parent_hierarchy_level"]
value_column = cfg["value_column"]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
id_system = cfg["id_system"]
region_list = cfg["region_list"]

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
    value_dict, error_dict = average_value_dicts(all_values)
else:
    value_dict, error_dict = all_values[0], None

values = []
standard_errors = []
region_names = []
region_colors = []
parent_labels = []

for region_id, value in value_dict.items():
    region_names.append(id_mapping.get(region_id))
    region_colors.append(f"#{color_mapping.get(region_id)}")
    parent_labels.append(child_to_parent_dict.get(region_id))
    values.append(value)

    if error_dict:
        standard_errors.append(error_dict.get(region_id))

for i in range(len(parent_labels) - 1):
    if parent_labels[i] == "":
        parent_labels[i] = parent_labels[i + 1]

if n > 1:
    create_barplot(
        save_path,
        region_names,
        values,
        region_colors,
        parent_labels,
        plot_title,
        value_name,
        yerr=standard_errors,
        selected_hierarchy=selected_hierarchy,
        specified_parent=specified_parent,
    )
else:
    create_barplot(
        save_path,
        region_names,
        values,
        region_colors,
        parent_labels,
        plot_title,
        value_name,
        selected_hierarchy=selected_hierarchy,
        specified_parent=specified_parent,
    )
