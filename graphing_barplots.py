import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
import sys
from utils import prepare_hierarchy_info, create_child_to_parent_mapping, load_and_prepare_data
from utils import collect_values_by_hierarchy, collect_values_directly, create_barplot, average_value_dicts

"""

BACKGROUND

This script allows you to plot barplots for two or more groups. Bars will be color coded by the Allen atlas hierarchy, and shaded differently
per group.

You can choose which level of the Allen CCF hierarchy to plot the graphs at. The full hierarchy option will give you the finest granularity.
Custom levels 1 through 7 are increasingly coarse levels. For this particular plot, Levels 4 through 7 are usually suitable if a parent is not
specified. Finer levels should be plotted with a parent specified to avoid too crowded graphs. 

Available hierarchy levels:

        "FullHierarchy"
        "CustomLevel1_gm"
        "CustomLevel1_wm"
        "CustomLevel2_gm"
        "CustomLevel3_gm"
        "CustomLevel4_gm"
        "CustomLevel5_gm"
        "CustomLevel6_gm"
        "CustomLevel7_gm"

The specified parent must be the name of a region at a coarser hierarchy level than the selected hierarchy, and this name must exist on the specified
parent_hierarchy_level. The different hierarchy levels available can be found as excel files in the files folder of this repository. The default parent
hierarchy level is Allen_STlevel_5, and this works well for most purposes. 

Available grey matter parents at this level include:
Isocortex, Olfactory areas, Hippocampal formation, Cortical subplate, Striatum, Pallidum, Thalamus, Hypothalamus, Midbrain, Pons, Medulla, Cerebellum

Available white matter, ventricular and other parents at this level include:	
cranial nerves, cerebellum related, fiber tracts, lateral forebrain bundle system, extrapyramidal fiber systems, medial forebrain bundle system,	
ventricular systems, grooves, retina, supra-callosal cerebral white matter, fiber tracts & ventricular system

If you want to plot very regions at the FullHierarchy level, you might want to choose a finer parent hierarchy level. You can always refer to the CustomLevel
excel files to figure out which parents are available at which levels. 

"""

#### USER INPUTS
files = [
    Path(r"example\path\your_file_1.csv"), 
    Path(r"example\path\your_file_2.csv"),  
    Path(r"example\path\your_file_3.csv")
]

# Choose your hierarchy level and optionally a parent level (refer to the background section above for details)
selected_hierarchy = "CustomLevel2_gm"
specified_parent = "Isocortex" # Set to None if you want to plot data from the selected hierarchy level across the brain
parent_hierarchy_level = "Allen_STlevel_5"

# Choose the metric you want to plot. Use "cell_counted" for absolute numbers, "cell_value" for values and "ROI_Volume_mm_3" for region volumes
value_column = "cell_counted"

# Choose a prefix that will be added to your saved file name
out_filename_prefix = "Example_barplot_multiSamples"

# Set the path to where you want your plots to be saved
out_path = Path(r"C:\Users\Ingvild\GitHub\visualization_scripts\example_graphs")

# Choose the output format. tif is good for images to be used in presentation. svg is good if you want to further 
# edit the figure, e.g. for using it in a publication figure or poster.
out_format = "png"

# Choose a title for your plot
plot_title = "Cell density"

# Specify whether your data files uses the original Allen ID system ("OriginalAllen") or 16-bit IDs as used by the Kim lab (KimLab16bit)
id_system = "KimLab16bit"

# If you just want to plot one or a few regions, add them to a list here. 
# These can be at any level of the hierarchy
# Example: ["Frontal pole, cerebral cortex", "Striatum", "Thalamus"]
# If you want to plot by the hierarchy, leave the list blank, i.e. []
region_list = []

#### MAIN CODE, do not change

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}.{out_format}")
else:
    save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}.{out_format}")

n = len(files)

if value_column == "cell_density":
    value_name = "Density"
elif value_column == "cell_counted":
    value_name = "Cell number"
elif value_column == "ROI_Volume_mm_3":
    value_name = "Region volume"

# Prepare value data
all_values = []

for file in files:

    if id_system == "KimLab16bit":
        data_file = load_and_prepare_data(file, allen2intfile)
    elif id_system == "OriginalAllen":
        data_file = load_and_prepare_data(file, allen2intfile, reverse=False)
    else:
        print("ID system not recognized. Must be KimLab16bit or OriginalAllen")
        sys.exit(1)
    
    id_mapping, color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, parent_hierarchy_level)

    # Collect values in a dictionary with region IDs
    if region_list:
        values_in_file = collect_values_directly(data_file, value_column, region_list, id_mapping)
    else:
        values_in_file = collect_values_by_hierarchy(data_file, value_column, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent)

    all_values.append(values_in_file)

# Get average values and SEM if n>1
if n > 1:
    value_dict, se_dict = average_value_dicts(all_values)
else:
    value_dict, se_dict = all_values[0], None


# Prepare lists for plotting
values = []
standard_errors = []
region_names = []
region_colors = []
parent_labels = []

for key, value in value_dict.items():
    region_id = key
    value = value
    region_name = id_mapping.get(region_id)
    region_color = f"#{color_mapping.get(region_id)}"
    parent_region = child_to_parent_dict.get(region_id)
    
    values.append(value)
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
    create_barplot(save_path, region_names, values, region_colors, parent_labels, plot_title, value_name,
                   yerr=standard_errors, selected_hierarchy=selected_hierarchy, specified_parent=specified_parent)
else:
    create_barplot(save_path, region_names, values, region_colors, parent_labels, plot_title, value_name,
                   selected_hierarchy=selected_hierarchy, specified_parent=specified_parent)
