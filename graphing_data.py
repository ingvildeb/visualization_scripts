import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import json
from collections import defaultdict
from glob import glob
from pathlib import Path

## PATH SETUP (do not change)

# Set the base path to the current script
base_path = Path(__file__).parent.resolve()

# Define file paths using pathlib
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"

#### USER INPUTS
file = base_path / "files" / "counted_3d_cells.csv" # Set path to your data file (example data used here)
out_filename_prefix = "example_filename" # Enter a prefix which will be used when saving your plots
out_format = "tif" # Choose your desired output format; could be png, tif, svg, jpg, pdf

# Set your desired level for displaying bars. Options available are listed below
hierarchy = "FullHierarchy"

"""
Options for hierarchy variable:

    - FullHierarchy: no grouping, all regions plotted as separate bars

    Grey matter focused hierarchies, with level 1 being most detailed and 7 most coarse
    - CustomLevel1_gm
    - CustomLevel2_gm
    - CustomLevel3_gm
    - CustomLevel4_gm
    - CustomLevel5_gm
    - CustomLevel6_gm
    - CustomLevel7_gm

    White matter focused hierarchy: white matter fully broken out with grey matter regions collapsed
    - CustomLevel1_wm

"""

##### DATA FORMATTING AND PREP

## PREPARE THE DATA TO BE PLOTTED
data_file = pd.read_csv(file)

# Create reverse mapping from 16-bit ids to original ids
allen2int = pd.read_excel(allen2intfile)
allen2int_dict = dict(zip(allen2int.iloc[:, 0], allen2int.iloc[:, 1]))
int2allen_dict = {v: k for k, v in allen2int_dict.items()}

# Create a copy of data_file with original ids
data_file_allen_ids = data_file.copy()
data_file_allen_ids['ROI_id'] = data_file['ROI_id'].map(int2allen_dict).fillna(data_file['ROI_id'])


## PREPARE THE HIERARCHY INFORMATION

# List of hierarchy names
hierarchy_names = [
    "Allen_STlevel_5",
    "CustomLevel1_gm",
    "CustomLevel1_wm",
    "CustomLevel2_gm",
    "CustomLevel3_gm",
    "CustomLevel4_gm",
    "CustomLevel5_gm",
    "CustomLevel6_gm",
    "CustomLevel7_gm",
    "FullHierarchy"
]

# Create a dictionary to store the paths
hierarchy_paths = {name: custom_hier_path / f"{name}.xlsx" for name in hierarchy_names}
grouped_hierarchies = ["CustomLevel1_gm", "CustomLevel2_gm", "CustomLevel3_gm", "FullHierarchy"]

# Read information from Allen atlas hierarchy file
with open(hierarchy_file, 'r') as file:
    json_data = json.load(file)

# Function to get mappings between fields in the json file, creating a dictionary of those values
def get_mappings(data, key_property, value_property, default_value=None):
    mapping = {}

    def recursive_collect(node):
        key = node.get(key_property)
        value = node.get(value_property, default_value)
        if key is not None and value is not None:
            mapping[key] = value
        
        for child in node.get('children', []):
            recursive_collect(child)

    for entry in data['msg']:
        recursive_collect(entry)
    
    return mapping

# Mapping names to ids and ids to colors
id_mapping = get_mappings(json_data, 'name', 'id')
color_mapping = get_mappings(json_data, 'id', 'color_hex_triplet')

# Function to format the custom region xlsx files into a list of regions per hierarchy
def format_custom_regions(file, id_mapping):
    # Read Excel file
    read_file = pd.read_excel(file)
    regions = read_file.columns.tolist()
    regions.remove("Custom brain region")
    if "root" in regions:
        regions.remove("root")

    region_ids = []
    for name in regions:
        i = id_mapping.get(name)
        region_ids.append(i)
    
    return region_ids

# Create a dictionary to store the results of format_custom_regions
hierarchy_regions = {
    name: format_custom_regions(path, id_mapping) 
    for name, path in hierarchy_paths.items()
}

## Prepare to use the Allen ST level 5 as a grouping level
grouping_data = pd.read_excel(hierarchy_paths.get("Allen_STlevel_5"))
grouping_data = grouping_data.drop(index=grouping_data.index[0])  # Drop the first row
grouping_data = grouping_data.drop(columns=grouping_data.columns[0])  # Drop the first column

# Initialize the child-to-parent dictionary
child_to_parent_dict = {}

# Iterate over each column (parent regions) in the DataFrame
for parent_region in grouping_data.columns:
    children = grouping_data[parent_region].dropna()
    for child in children:
        child_to_parent_dict[child] = parent_region

#### GRAPHING THE DATA

# Initialize variables
densities = []
region_names = []
region_colors = []
parent_labels = []

# Populate the data for plotting and obtain the coarse parent mappings
for region in hierarchy_regions.get(hierarchy, []):
    region_id = data_file_allen_ids.loc[data_file_allen_ids["ROI_id"] == region, "ROI_id"].values[0]
    density = data_file_allen_ids.loc[data_file_allen_ids["ROI_id"] == region, "cell_density"].values[0]
    region_name = data_file_allen_ids.loc[data_file_allen_ids["ROI_id"] == region, "ROI_name"].values[0]
    region_color = color_mapping.get(region_id)
    region_color = f"#{region_color}"

    densities.append(density)
    region_names.append(region_name)
    region_colors.append(region_color)

    # Find the parent region for the current region
    parent_region = child_to_parent_dict.get(region_id, '')
    parent_labels.append(parent_region)

# Assign parent where missing using subsequent parent's assignment. It works because these are only the higher-level regions that always appear before their more granular parts.
for i in range(len(parent_labels) - 1):
    if parent_labels[i] == '':
        parent_labels[i] = parent_labels[i + 1]

# Function to draw brackets when grouping labels on the x axis
def add_bracket(ax, x_range, y_pos=1.05, line_width=2):
    start, end = x_range
    ax.annotate('', xy=(start, y_pos), xytext=(end, y_pos),
                arrowprops=dict(arrowstyle='-', lw=line_width, color='black'),
                annotation_clip=False, xycoords=('data', 'axes fraction'), textcoords=('data', 'axes fraction'))

# Plot the data
fig, ax = plt.subplots(figsize=(35, 15))
ax.bar(region_names, densities, color=region_colors)

ax.set_ylabel('Density', fontsize=16)
ax.set_title('MOBP cell densities', fontsize=20)
ax.set_xticklabels(region_names, rotation=45, ha='right', fontsize=16)


# Grouping the x axis for the most granular hierarchies

if hierarchy in grouped_hierarchies:
    # Hide the main x-axis labels
    ax.set_xticklabels([])
    ax.tick_params(axis='x', which='both', bottom=False, top=False)

    # Create a secondary x-axis for the parent groups
    sec_ax = ax.secondary_xaxis('bottom')
    sec_ax.tick_params(axis='x', which='both', bottom=False, top=False)

    # Determine positions for group labels
    unique_parents = list(dict.fromkeys(parent_labels))  # Unique, ordered parents
    group_boundaries = []
    group_positions = []
    parent_names = []

    for parent in unique_parents:
        indices = [i for i, x in enumerate(parent_labels) if x == parent]
        if indices:
            start_index, end_index = indices[0], indices[-1]
            group_boundaries.append((start_index, end_index))
            group_positions.append((start_index + end_index) / 2)
        
        # Original mapping from IDs to meaningful parent names or titles
        parent_names.append(parent)
    
    sec_ax.set_xticks(group_positions)
    sec_ax.set_xticklabels(parent_names, rotation=45, ha='right', fontsize=16)

    plt.subplots_adjust(bottom=0.2)

    # Bracket application
    for start, end in group_boundaries:
        add_bracket(ax, (start, end), y_pos=-0.005, line_width=2)

plt.tight_layout()

# Output path for plots
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)  # Creates the directory if it doesn't exist

plt.savefig(out_path / f"{out_filename_prefix}_{hierarchy}.{out_format}")
plt.show()

