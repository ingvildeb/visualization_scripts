import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import numpy as np
from scipy import stats
from utils import prepare_hierarchy_info, create_child_to_parent_mapping, load_and_prepare_data
from utils import collect_densities, average_density_dicts, perform_t_tests, calculate_averages_per_group, plot_bar_chart

#### USER INPUTS
IDs_to_files_dict = {
    "CS0290": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0290_counted_3d_cells.csv"), 
    "CS0291": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0291_counted_3d_cells.csv"), 
    "CS0292": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0292_counted_3d_cells.csv"), 
    "CS0293": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
    "CS0294": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0294_counted_3d_cells.csv"),
    "CS0295": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0295_counted_3d_cells.csv"),
}

grouping = {
    "CS0290": "Wildtype", 
    "CS0291": "Wildtype", 
    "CS0292": "Wildtype", 
    "CS0293": "Wildtype",
    "CS0294": "TgSwDI",
    "CS0295": "TgSwDI",
} 

groups = list(set(grouping.values()))
num_groups = len(groups)

out_filename_prefix = "NeuN_18mo_C57_vs_14mo_TgSwDI--"
out_format = "tif"
plot_title = "NeuN cell densities" 
selected_hierarchy = "CustomLevel4_gm"
specified_parent = None
apply_t_test = True  # Set this to True or False as needed

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_.{out_format}")

if num_groups > 2:
    if apply_t_test:
        print(f"Not able to apply t-test for n = {num_groups} groups. Consider another statistical test.")
        apply_t_test = False

# Prepare individual density data
all_individual_densities = {}  # Store individual densities in a dictionary of dictionaries for each group

for ID, file in IDs_to_files_dict.items():
    ID_group = grouping.get(ID)
    data_file = load_and_prepare_data(file, allen2intfile)
    id_mapping, color_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

    # Collect the densities
    densities_in_file = collect_densities(data_file, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent)

    for region_id, density in densities_in_file.items():
        if region_id not in all_individual_densities:
            all_individual_densities[region_id] = {}
        if ID_group not in all_individual_densities[region_id]:
            all_individual_densities[region_id][ID_group] = []
        all_individual_densities[region_id][ID_group].append(density)

# Prepare average densities and SE calculation from all_individual_densities
avg_densities_to_group_dict, se_to_region_group_dict, n_to_group_dict = calculate_averages_per_group(all_individual_densities)

# Create a dictionary to store bar values per region
regions = list(all_individual_densities.keys())
bar_values = {region: [] for region in regions}  # Initialize bar values as an empty list for each region

for region in regions:
    for group in groups:
        avg_value = avg_densities_to_group_dict.get(group, {}).get(region, 0)  # Default to 0 if no density
        bar_values[region].append(avg_value)

# Convert bar_values dictionary to an array for plotting
bar_values_array = np.array([bar_values[region] for region in regions])  # Create an array for plotting

# Create a color list based on region colors from color_mapping
region_colors = [f"#{color_mapping.get(region)}" for region in regions]

# Conditional t-test based on apply_t_test flag
if apply_t_test:
    significant_results = perform_t_tests(all_individual_densities, 'Wildtype', 'TgSwDI')
else:
    significant_results = {region: None for region in regions}

# Plot bar chart
plot_bar_chart(regions, id_mapping, bar_values_array, se_to_region_group_dict, significant_results, groups, n_to_group_dict, region_colors, plot_title, save_path)
