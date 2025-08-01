import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
import numpy as np
import altair as alt
from utils import prepare_hierarchy_info, get_descriptive_stats, prepare_groupwise_values_dict

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
Isocortex, Olfactory areas, Hippocampal formation, Cortical subplate, Striat, Pallidum, Thalamus, Hypothalamus, Midbrain, Pons, Medulla, Cerebellum

Available white matter, ventricular and other parents at this level include:	
cranial nerves, cerebellum related, fiber tracts, lateral forebrain bundle system, extrapyramidal fiber systems, medial forebrain bundle system,	
ventricular systems, grooves, retina, supra-callosal cerebral white matter, fiber tracts & ventricular system

If you want to plot very regions at the FullHierarchy level, you might want to choose a finer parent hierarchy level. You can always refer to the CustomLevel
excel files to figure out which parents are available at which levels. 

"""

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

# Assign each ID to a group. The order that you add the groups here will dictate the order of bars in your chart.
grouping = {
    "IEB0079": "P04",
    "IEB0078": "P04",
    "IEB0066": "P08", 
    "IEB0068": "P08",
    "IEB0039": "P14", 
    "IEB0040": "P14", 
    "LJS011": "P14",
} 


# Choose the metric you want to plot. Use "cell_counted" for absolute numbers, "cell_value" for values and "ROI_Volume_mm_3" for region volumes
value_column = "cell_density"

# Choose your hierarchy level and optionally a parent level (refer to the background section above for details)
selected_hierarchy = "CustomLevel1_gm"
specified_parent = "Isocortex"  # Set to False if you want to plot data from the selected hierarchy level across the brain
parent_hierarchy_level = "Allen_STlevel_5"

# Choose a prefix that will be added to your saved file name
out_filename_prefix = "Aldh_"

# Choose the output format. tif is good for images to be used in presentation. svg is good if you want to further 
# edit the figure, e.g. for using it in a publication figure or poster.
out_format = "png"

# Choose a title for your plot
plot_title = "Aldh cell densities"

# Select a title for your x axis (typically what the groups are based on)
x_axis_title = "Age"


#### MAIN CODE
groups = []
for id, group in grouping.items(): 
    if group not in groups:
        groups.append(group)

num_groups = len(groups)

if value_column == "cell_density":
    value_name = "Density"
elif value_column == "cell_counted":
    value_name = "Cell number"
elif value_column == "ROI_Volume_mm_3":
    value_name = "Region volume"

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}.{out_format}")


# Prepare groupwise data
id_mapping, color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
all_individual_values = prepare_groupwise_values_dict(IDs_to_files_dict, grouping, value_column, allen2intfile, selected_hierarchy,
                                                       specified_parent, hierarchy_regions, custom_hier_path, parent_hierarchy_level)

# Prepare average values and SE of values from the groupwise data
avg_values_to_group_dict, se_to_region_group_dict, n_to_group_dict = get_descriptive_stats(all_individual_values)

# Data preparation for Altair Directly from avg_values_to_group_dict
# Convert avg_values_to_group_dict into a pandas DataFrame suitable for plotting
region_names = list(avg_values_to_group_dict.keys())
data = []

for region in region_names:
    for group in groups:
        avg_value = avg_values_to_group_dict.get(region, {}).get(group, 0)
        se_value = se_to_region_group_dict.get(region, {}).get(group, 0)
        data.append({
            'Region': id_mapping.get(region, region),  # Mapping region_id to a readable name
            'Group': group,
            'Average': avg_value,
            'SE': se_value
        })

# Create DataFrame for Altair
altair_df = pd.DataFrame(data)

# Create the heatmap
heatmap = alt.Chart(altair_df).mark_rect().encode(
    x=alt.X('Group:O', title=x_axis_title, sort=groups),
    y=alt.Y('Region:O', sort=region_names, title='Regions'),
    color='Average:Q',
    tooltip=['Region', 'Group', 'Average', 'SE']  # Include SE in tooltip if desired
).properties(
    title=plot_title
).configure_axis(
    labelLimit=200   # Increase label limit to reduce truncation (may depend on your specific use case)
)

heatmap.save(str(save_path))  # Save Altair plot
heatmap.display()  # Display the plot
