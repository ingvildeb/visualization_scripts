import sys
from pathlib import Path

import altair as alt
import pandas as pd

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import (
    load_script_config,
    normalize_user_path,
    require_absolute_path,
    require_file,
)
from utils.atlas_data_prep import prepare_groupwise_values_dict, prepare_hierarchy_info
from utils.stats import get_descriptive_stats


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
cfg = load_script_config(script_path, "tabular_heatmap", test_mode=test_mode)

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
x_axis_title = cfg["x_axis_title"]
orientation = cfg["orientation"]
id_system = cfg["id_system"]
error_metric = cfg["error_metric"]
color_scheme = cfg["color_scheme"]

# -------------------------
# PATHS
# -------------------------
repo_root = script_path.parent.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}_{orientation}.{out_format}"
else:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}_{orientation}.{out_format}"

# -------------------------
# MAIN
# -------------------------
groups = ordered_unique(grouping.values())

id_mapping, _color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

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
error_label = "SE" if error_metric == "se" else "SD"

region_names = list(avg_values_to_group_dict.keys())
data = []
for region in region_names:
    for group in groups:
        avg_value = avg_values_to_group_dict.get(region, {}).get(group, 0)
        error_value = error_to_region_group_dict.get(region, {}).get(group, 0)
        data.append(
            {
                "Region": id_mapping.get(region, region),
                "Group": group,
                "Average": avg_value,
                error_label: error_value,
            }
        )

altair_df = pd.DataFrame(data)

if orientation == "vertical":
    heatmap = (
        alt.Chart(altair_df)
        .mark_rect()
        .encode(
            x=alt.X("Group:O", title=x_axis_title, sort=groups),
            y=alt.Y("Region:O", sort=region_names, title="Regions"),
            color=alt.Color("Average:Q", scale=alt.Scale(scheme=color_scheme)),
            tooltip=["Region", "Group", "Average", error_label],
        )
        .properties(title=plot_title)
        .configure_axis(labelLimit=200)
    )
    heatmap.save(str(save_path))
    heatmap.display()
elif orientation == "horizontal":
    heatmap = (
        alt.Chart(altair_df)
        .mark_rect()
        .encode(
            x=alt.X(
                "Region:O",
                sort=region_names,
                axis=alt.Axis(labelFontSize=12, titleFontSize=14, labelAngle=45),
            ),
            y=alt.Y(
                "Group:O",
                title=x_axis_title,
                sort=groups,
                axis=alt.Axis(labelFontSize=12, titleFontSize=14),
            ),
            color=alt.Color("Average:Q", scale=alt.Scale(scheme=color_scheme)),
            tooltip=["Region", "Group", "Average", error_label],
        )
        .properties(title=plot_title, width=1000, height=50)
        .configure_axis(labelLimit=300)
    )
    heatmap.save(str(save_path))
    heatmap.display()
else:
    raise RuntimeError("orientation must be 'vertical' or 'horizontal'")
