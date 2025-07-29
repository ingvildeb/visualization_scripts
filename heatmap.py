import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
import numpy as np
import altair as alt
from utils import prepare_hierarchy_info, add_bracket, create_child_to_parent_mapping, create_reverse_id_mapping, load_and_prepare_data
from utils import collect_densities, create_barplot, average_density_dicts, normalize_density_values, create_heatmap, calculate_averages_per_group


#### USER INPUTS
IDs_to_files_dict = {
    "IEB0039": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0039_counted_3d_cells.csv"), 
    "IEB0040": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0040_counted_3d_cells.csv"), 
    "IEB0066": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0066_counted_3d_cells.csv"), 
    "IEB0068": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0068_counted_3d_cells.csv"),
    "IEB0079": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0079_counted_3d_cells.csv"),
    "LJS011": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\LJS011_counted_3d_cells.csv"),
    "IEB0078": Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0078.FIRSTIMAGE_counted_3d_cells.csv"),
}

grouping = {
    "IEB0039": "P14", 
    "IEB0040": "P14", 
    "IEB0066": "P08", 
    "IEB0068": "P08",
    "IEB0079": "P04",
    "IEB0078": "P04",
    "LJS011": "P14",
} 

groups_based_on = "Age"


out_filename_prefix = "Aldh_"
out_format = "png"
plot_title = "Aldh cell densities"
selected_hierarchy = "CustomLevel1_gm"
specified_parent = "Thalamus"


#### MAIN CODE, do not change

groups = list(set(grouping.values()))
num_groups = len(groups)

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}.{out_format}")
n = len(IDs_to_files_dict)


# Prepare individual density data
all_individual_densities = {}  # Store individual densities in a dictionary of dictionaries for each group

for ID, file in IDs_to_files_dict.items():
    ID_group = grouping.get(ID)
    data_file = load_and_prepare_data(file, allen2intfile)
    id_mapping, color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
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
regions_names = [id_mapping.get(region_id, region_id) for region_id in regions]  # Use region_id to get names
density_values = {region: [] for region in regions}  # Initialize density values as an empty list for each region

for region in regions:
    for group in groups:
        avg_value = avg_densities_to_group_dict.get(group, {}).get(region, 0)  # Default to 0 if no density
        density_values[region].append(avg_value)

# Convert bar_values dictionary to an array for plotting
density_values_array = np.array([density_values[region] for region in regions])  # Create an array for plotting

# Convert your heatmap data to a pandas DataFrame
df = pd.DataFrame(density_values_array, columns=groups, index=regions_names)  # Use names as index

# Melt the DataFrame to long format for Altair
df_melted = df.reset_index().melt(id_vars='index', var_name=groups_based_on, value_name='Density')
df_melted.columns = ['Region', groups_based_on, 'Density']

# Create the heatmap
heatmap = alt.Chart(df_melted).mark_rect().encode(
    x=alt.X(f'{groups_based_on}:O', title=groups_based_on),  # Set the title of the x-axis
    y=alt.Y('Region:O', sort=regions_names, title='Regions'),
    color='Density:Q',
    tooltip=['Region', groups_based_on, 'Density']
).properties(
    title=plot_title
).configure_axis(
    labelLimit=200   # Increase label limit to reduce truncation (may depend on your specific use case)
)

heatmap.save(str(save_path))  # Save Altair plot
heatmap.display()  # Display the plot
