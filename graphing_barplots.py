import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
from utils import prepare_hierarchy_info, add_bracket, create_child_to_parent_mapping, create_reverse_id_mapping, load_and_prepare_data
from utils import collect_densities, create_barplot, average_density_dicts, normalize_density_values, create_heatmap


#### USER INPUTS
files = [
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0290_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0291_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0292_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0294_counted_3d_cells.csv"),
    # Add more subject files as needed
]

out_filename_prefix = "NeuN_P533_C57_"
out_format = "tif"
plot_title = "NeuN cell densities"
selected_hierarchy = "CustomLevel1_gm"
specified_parent = "Hippocampal formation"

#### MAIN CODE, do not change


# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}.{out_format}")
n = len(files)

# Prepare density data
all_densities = []

for file in files:
    data_file = load_and_prepare_data(file, allen2intfile)
    id_mapping, color_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

    # Collect the densities and corresponding region names, colors and parent regions
    densities_in_file = collect_densities(data_file, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent)
    all_densities.append(densities_in_file)

all_densities_normalized = normalize_density_values(all_densities)

# Get average densities and SEM if n>1
if n > 1:
    density_dict, se_dict = average_density_dicts(all_densities)
else:
    density_dict, se_dict = all_densities[0], None


# Prepare lists for plotting
densities = []
standard_errors = []
region_names = []
region_colors = []
parent_labels = []

for key, value in density_dict.items():
    region_id = key
    density = value
    region_name = id_mapping.get(region_id)
    region_color = f"#{color_mapping.get(region_id)}"
    parent_region = child_to_parent_dict.get(region_id)
    
    densities.append(density)
    region_names.append(region_name)
    region_colors.append(region_color)
    parent_labels.append(parent_region)
    
    if se_dict:
        standard_error = se_dict.get(region_id)
        standard_errors.append(standard_error)

# Assign parent where missing
for i in range(len(parent_labels) - 1):
    if parent_labels[i] == '':
        parent_labels[i] = parent_labels[i + 1]

if n > 1:
    create_barplot(save_path, region_names, densities, region_colors, parent_labels, plot_title, yerr=standard_errors, selected_hierarchy = selected_hierarchy, specified_parent = specified_parent)
else:
    create_barplot(save_path, region_names, densities, region_colors, parent_labels, plot_title, selected_hierarchy = selected_hierarchy, specified_parent = specified_parent)
