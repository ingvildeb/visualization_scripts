import sys
from pathlib import Path
import brainglobe_heatmap as bgh
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
    create_child_to_parent_mapping,
    load_and_prepare_data,
    prepare_hierarchy_info,
)
from utils.stats import average_value_dicts

# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "atlas_heatmaps", test_mode=test_mode)

# -------------------------
# CONFIG PARAMETERS
# -------------------------
files = [
    require_file(
        require_absolute_path(normalize_user_path(p), f"Input CSV file #{i + 1}"),
        f"Input CSV file #{i + 1}",
    )
    for i, p in enumerate(cfg["files"])
]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
selected_hierarchy = cfg["selected_hierarchy"]
colormap = cfg["colormap"]
n = cfg["n"]
orientation = cfg["orientation"]
id_system = cfg["id_system"]

# -------------------------
# PATHS
# -------------------------
repo_root = script_path.parent.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path = out_path / f"{out_filename_prefix}_{orientation}_atlasHeatmaps"
out_path.mkdir(parents=True, exist_ok=True)

# -------------------------
# MAIN
# -------------------------
value_column = "cell_density"

all_values = []
for file in files:
    if id_system == "KimLab16bit":
        data_file = load_and_prepare_data(file, allen2intfile)
    elif id_system == "OriginalAllen":
        data_file = load_and_prepare_data(file, allen2intfile, reverse=False)
    else:
        raise RuntimeError("ID system not recognized. Must be KimLab16bit or OriginalAllen")

    id_mapping, _color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

    values_in_file = collect_values_by_hierarchy(
        data_file,
        value_column,
        hierarchy_regions,
        selected_hierarchy,
        child_to_parent_dict,
    )
    all_values.append(values_in_file)

density_dict, _ = average_value_dicts(all_values)

values = {}
for key, value in density_dict.items():
    region_abb = acronym_mapping.get(key)
    if region_abb is not None:
        values[region_abb] = value

min_value = min(values.values())
max_value = max(values.values())

if orientation == "frontal":
    common_xlim = (6000, -6000)
    common_ylim = (5000, -5000)
    positions = np.linspace(1000, 12000, n).tolist()
elif orientation == "sagittal":
    common_xlim = (8000, -8000)
    common_ylim = (5000, -5000)
    positions = np.linspace(1000, 5000, n).tolist()
elif orientation == "horizontal":
    common_xlim = (6000, -6000)
    common_ylim = (6000, -8000)
    positions = np.linspace(1000, 7000, n).tolist()
else:
    raise RuntimeError("orientation must be frontal, sagittal, or horizontal")

width = abs(common_xlim[1] - common_xlim[0])
height = abs(common_ylim[1] - common_ylim[0])

for i, position in enumerate(positions):
    aspect_ratio = height / width
    fig_width = 8
    fig_height = fig_width * aspect_ratio

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    heatmap = bgh.Heatmap(
        values,
        position=position,
        orientation=orientation,
        vmin=min_value,
        vmax=max_value,
        cmap=colormap,
        format="2D",
    )

    heatmap.plot_subplot(
        fig,
        ax,
        show_legend=False,
        xlabel="um",
        ylabel="um",
        hide_axes=False,
        cbar_label=None,
        show_cbar=False,
    )

    ax.set_xlim(common_xlim)
    ax.set_ylim(common_ylim)

    cbar_ax = fig.add_axes([0.9, 0.5, 0.02, 0.3])
    norm = plt.Normalize(vmin=min_value, vmax=max_value)
    plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=colormap), cax=cbar_ax)

    plt.savefig(out_path / f"{i + 1}_position{int(position)}.{out_format}", format=out_format)
    plt.show()
    plt.close()

print("All heatmaps saved successfully.")
