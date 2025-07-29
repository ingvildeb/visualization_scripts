import brainglobe_heatmap as bgh
import matplotlib.pyplot as plt
from pathlib import Path
from utils import prepare_hierarchy_info, load_and_prepare_data, collect_densities, average_density_dicts

# Define the files and other inputs
files = [
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0039_counted_3d_cells.csv"), 
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\IEB0040_counted_3d_cells.csv"), 
    Path(r"Z:\Labmembers\Ingvild\Cellpose\Aldh_model\cell density analysis\LJS011_counted_3d_cells.csv"),
]

out_filename_prefix = "Aldh_P14_atlasHeatmaps"
out_format = "tif"
selected_hierarchy = "CustomLevel1_gm"

# Path setup
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)

# Prepare density data
all_densities = []
for file in files:
    data_file = load_and_prepare_data(file, allen2intfile)
    id_mapping, color_mapping, acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)
    child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

    # Collect the densities
    densities_in_file = collect_densities(data_file, hierarchy_regions, selected_hierarchy, child_to_parent_dict)
    all_densities.append(densities_in_file)

# Get average densities
density_dict, _ = average_density_dicts(all_densities)

# Prepare a dictionary for plotting
values = {}
for key, value in density_dict.items():
    region_abb = acronym_mapping.get(key)
    if region_abb is not None:
        values[region_abb] = value

min_density = min(values.values())
max_density = max(values.values())

# Create a figure for multiple heatmaps
positions = [1000, 3000, 5000, 7000, 9000, 11000]
n_rows = (len(positions) + 1) // 2  # Calculate number of rows
fig, axs = plt.subplots(n_rows, 2, figsize=(12, n_rows * 5))  # Create subplots

# Flatten axes for easier indexing
axs = axs.flatten()

# Common limits for axes
common_xlim = (6000, -6000)
common_ylim = (4000, -4000)

# Plotting heatmaps
for i, position in enumerate(positions):
    heatmap = bgh.Heatmap(
        values,
        position=position,
        orientation="frontal",
        vmin=min_density,
        vmax=max_density,
        cmap='viridis',
        format="2D"
    )
    heatmap.plot_subplot(fig, axs[i], show_legend=False, xlabel='µm', ylabel='µm', hide_axes=True, cbar_label=None, show_cbar=False)

    # Set common limits for x and y axes
    axs[i].set_xlim(common_xlim)
    axs[i].set_ylim(common_ylim)

# Create a shared colorbar in the upper left of the first subplot
cbar_ax = fig.add_axes([0.1, 0.72, 0.02, 0.15])  # Adjust these values as necessary
norm = plt.Normalize(vmin=min_density, vmax=max_density)
cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap='viridis'), cax=cbar_ax)
cbar.set_label('Density', rotation=270, labelpad=15)

# Adjust layout
#plt.subplots_adjust(hspace=0.1)  # Adjust vertical spacing between subplots

# Save the final combined figure
plt.savefig(Path(out_path / f"{out_filename_prefix}_combined_heatmaps.{out_format}"), format=out_format)
plt.show()  # Show the final plot
