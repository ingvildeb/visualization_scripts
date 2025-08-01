import brainglobe_heatmap as bgh
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import sys
from utils import prepare_hierarchy_info, load_and_prepare_data, collect_values, average_value_dicts, create_child_to_parent_mapping


"""

BACKGROUND

This script allows you to plot Brainglobe style heatmaps from a selected number of positions.
The number of plates selected will be plotted from the olfactory bulb to cerebellum with regular intervals.

You can choose which level of the Allen CCF hierarchy to plot the plates at. The full hierarchy option will give you the finest granularity.
Custom levels 1 through 7 are increasingly coarse levels. For this particular plot, Level 1 is usually suitable. It gives fine detail but 
merges some very fine regions such as cortical layers. If you know your signal to have layer-specific distribution, you might want to use
the full hierarchy. Available hierarchy levels:

        "FullHierarchy"
        "CustomLevel1_gm"
        "CustomLevel1_wm"
        "CustomLevel2_gm"
        "CustomLevel3_gm"
        "CustomLevel4_gm"
        "CustomLevel5_gm"
        "CustomLevel6_gm"
        "CustomLevel7_gm"

CITATION POLICY

If you use these plots in a publication or poster, make sure to cite the brainglobe-heatmap package according to their citation policy:

Federico Claudi, Adam Tyson, Luigi Petrucco, Mathieu Bourdenx, Carlo Castoldi, Rami Hamati, & Alessandro Felder. 
(2024). brainglobe/brainglobe-heatmap. Zenodo. https://doi.org/10.5281/zenodo.10375287

"""

#### USER INPUTS

# Define the files to be used. Heatmaps will represent an average of cell densities across these files.
files = [
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0039_counted_3d_cells.csv"), 
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0040_counted_3d_cells.csv"), 
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\LJS011_counted_3d_cells.csv"),
]

# Choose a prefix that will be added to your saved file name
out_filename_prefix = "Aldh_P14_" 

# Choose the output format. tif is good for images to be used in presentation. svg is good if you want to further 
# edit the figure, e.g. for using it in a publication figure or poster.
out_format = "svg" 

# Choose a hierarchy level to display brain regions at.
selected_hierarchy = "CustomLevel1_gm" 

# Choose your desired colormap. You can use standard matplotlib colormaps, 
# see https://matplotlib.org/stable/users/explain/colors/colormaps.html for an overview 
colormap = 'viridis' 

# Choose the number of atlas plates you want to plot. 
n = 12  

# Choose the orientation of your atlas plates. Options are frontal, sagittal and horizontal. 

orientation = "horizontal"

# Specify whether your data files uses the original Allen ID system ("OriginalAllen") or 16-bit IDs as used by the Kim lab (KimLab16bit)
id_system = "KimLab16bit"

### MAIN CODE, do not edit
# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots" / f"{out_filename_prefix}_{orientation}_atlasHeatmaps"
out_path.mkdir(parents=True, exist_ok=True)

# Set value column, only cell_density used for now
value_column = "cell_density"

# Prepare density data
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
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

    # Collect the densities
    values_in_file = collect_values(data_file, value_column, hierarchy_regions, selected_hierarchy, child_to_parent_dict)
    all_values.append(values_in_file)

# Get average values
density_dict, _ = average_value_dicts(all_values)


# Prepare a dictionary for plotting
values = {}
for key, value in density_dict.items():
    region_abb = acronym_mapping.get(key)
    if region_abb is not None: 
        values[region_abb] = value

min_value = min(values.values())
max_value = max(values.values())

# Parameters
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

# Calculate width and height from common_limits
width = abs(common_xlim[1] - common_xlim[0])
height = abs(common_ylim[1] - common_ylim[0])

# Plotting and saving individual heatmaps
for i, position in enumerate(positions):
    # Dynamically set the figure size based on the calculated aspect ratio
    aspect_ratio = height / width  # This ratio will define how the figure should scale
    fig_width = 8  # You can define a fixed width
    fig_height = fig_width * aspect_ratio  # Calculate height based on width and aspect ratio
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))  # Create the figure with the calculated size
    
    # Create the heatmap
    heatmap = bgh.Heatmap(
        values,
        position=position,
        orientation=orientation,
        vmin=min_value,
        vmax=max_value,
        cmap=colormap,
        format="2D"
    )

    # Plot heatmap in the subplot
    heatmap.plot_subplot(fig, ax, show_legend=False, xlabel='µm', ylabel='µm', hide_axes=False, cbar_label=None, show_cbar=False)

    # Set common limits for x and y axes
    ax.set_xlim(common_xlim)
    ax.set_ylim(common_ylim)

    # Color bar setup
    cbar_ax = fig.add_axes([0.9, 0.5, 0.02, 0.3])  # Adjust these values as necessary 
    norm = plt.Normalize(vmin=min_value, vmax=max_value) 
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=colormap), cax=cbar_ax)

    # Save the individual heatmap figure
    plt.savefig(Path(out_path / f"{i+1}_position{int(position)}.{out_format}"), format=out_format)
    plt.show()
    plt.close()  # Close the figure after saving to free memory

print("All heatmaps saved successfully.")