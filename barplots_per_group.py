import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import numpy as np
from scipy import stats
from utils import prepare_hierarchy_info, prepare_groupwise_values_dict, perform_t_tests, get_descriptive_stats, values_to_array, create_groupwise_barplot

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
IDs_to_files_dict = {
    "CS0290": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0290_counted_3d_cells.csv"), 
    "CS0291": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0291_counted_3d_cells.csv"), 
    "CS0292": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0292_counted_3d_cells.csv"), 
    "CS0293": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
    "CS0294": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0294_counted_3d_cells.csv"),
    "CS0295": Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0295_counted_3d_cells.csv"),
}


# Assign each ID to a group. The order that you add the groups here will dictate the order of bars in your chart.
# A good practice is to add the control group IDs first followed by experimental group; or lowest age first in case of age groups.
grouping = {
    "CS0290": "Wildtype", 
    "CS0291": "Wildtype", 
    "CS0292": "Wildtype", 
    "CS0293": "Wildtype",
    "CS0294": "TgSwDI",
    "CS0295": "TgSwDI",
} 

# Choose the metric you want to plot. Use "cell_counted" for absolute numbers, "cell_value" for values and "ROI_Volume_mm_3" for region volumes
value_column = "cell_density"

# Choose your hierarchy level and optionally a parent level (refer to the background section above for details)
selected_hierarchy = "CustomLevel1_gm"
specified_parent = "Isocortex" # Set to False if you want to plot data from the selected hierarchy level across the brain
parent_hierarchy_level = "Allen_STlevel_5"


# Choose a prefix that will be added to your saved file name
out_filename_prefix = "NeuN_18mo_C57_vs_14mo_TgSwDI--"

# Choose the output format. tif is good for images to be used in presentation. svg is good if you want to further 
# edit the figure, e.g. for using it in a publication figure or poster.
out_format = "tif"

# Choose a title for your plot
plot_title = "NeuN cell density"

# Set this to True or False as needed. Will only work with exactly two groups.
apply_t_test = True  

# Optional if you're not happy with the hatch patterns. Choose hatch patterns to cycle through in the bars for each group
hatch_patterns = ['', '///', '+++', '---', '+', 'x', 'o', 'O', '.']



#### MAIN CODE, do not edit

# Get the ordered list of unique groups based on the order of insertion
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
save_path = Path(out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_.{out_format}")

# Prepare groupwise data
id_mapping, color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

all_individual_values  = prepare_groupwise_values_dict(IDs_to_files_dict, grouping, value_column, allen2intfile, selected_hierarchy,
                                                       specified_parent, hierarchy_regions, custom_hier_path, parent_hierarchy_level)

# Prepare average values and SE of values from the groupwise data
avg_values_to_group_dict, se_to_region_group_dict, n_to_group_dict = get_descriptive_stats(all_individual_values)

# Prepare a value array and corresponding lists of regions and colors for plotting
values_array, regions, region_colors = values_to_array(all_individual_values, groups, avg_values_to_group_dict, color_mapping)

# Run t-test
# Check if t test is possible
if num_groups > 2:
    if apply_t_test:
        print(f"Not able to apply t-test for n = {num_groups} groups. Consider another statistical test.")
        apply_t_test = False

# Conditional t-test based on apply_t_test flag
if apply_t_test:
    significant_results = perform_t_tests(all_individual_values, groups[0], groups[1])
else:
    significant_results = {region: None for region in regions}

# Plot bar chart
create_groupwise_barplot(save_path, regions, id_mapping, values_array, se_to_region_group_dict, significant_results, 
                         groups, n_to_group_dict, region_colors, plot_title, hatch_patterns, value_name)
