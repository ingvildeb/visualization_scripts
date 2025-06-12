import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
import numpy as np
import plotly.graph_objects as go
from utils import prepare_hierarchy_info, add_bracket, create_child_to_parent_mapping, create_reverse_id_mapping, load_and_prepare_data
from utils import collect_densities, create_barplot, average_density_dicts, normalize_density_values, create_heatmap


#### USER INPUTS
files = [
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0290_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0291_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0292_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
    # Add more subject files as needed
]

out_filename_prefix = "CS0920_"
out_format = "png"
plot_title = "NeuN cell densities"
selected_hierarchy = "CustomLevel1_gm"
specified_parent = "Isocortex"
chart_type = "Heatmap"

#### MAIN CODE, do not change

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}.{out_format}")
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

# Prepare lists for plotting
densities = []
region_names = []
region_colors = []
parent_labels = []

for key, value in all_densities_normalized[0].items():
    region_id = key
    density = value
    region_name = id_mapping.get(region_id)
    region_color = f"#{color_mapping.get(region_id)}"
    parent_region = child_to_parent_dict.get(region_id)

    densities.append(density)
    region_names.append(region_name)
    region_colors.append(region_color)
    parent_labels.append(parent_region)

# Prepare 2D data for heatmap
regions = list(all_densities_normalized[0].keys())  # Get the region names
heatmap_data = np.zeros((len(regions), n))  # Create a 2D numpy array

# Fill in the heatmap data
for j, densities in enumerate(all_densities_normalized):
    for i, region in enumerate(regions):
        region_name = id_mapping.get(region)  # Get the region id
        print(f"Processing Case {j + 1}, Region: {region_name}, ID: {region}")  # Debug info
        if region in densities:
            heatmap_data[i, j] = densities[region]  # Fill in the value
        else:
            print(f"Warning: {region_id} not found in densities for Case {j + 1}.")  # Debug info

print("Heatmap Data:")  # After filling the heatmap data
print(heatmap_data)

import altair as alt
import pandas as pd

# Convert your heatmap data to a pandas DataFrame
df = pd.DataFrame(heatmap_data, columns=[f"Case {i + 1}" for i in range(n)], index=region_names)

# Melt the DataFrame to long format for Altair
df_melted = df.reset_index().melt(id_vars='index', var_name='Case', value_name='Density')
df_melted.columns = ['Region', 'Case', 'Density']

# Create the heatmap
heatmap = alt.Chart(df_melted).mark_rect().encode(
    x='Case:O',
    y='Region:O',
    color='Density:Q',
    tooltip=['Region', 'Case', 'Density']
).properties(
    title=plot_title
)

heatmap.save(str(save_path))  # Save Altair plot if needed
heatmap.display()  # Display the plot