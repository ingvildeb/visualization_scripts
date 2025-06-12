import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import numpy as np
from utils import prepare_hierarchy_info, add_bracket, create_child_to_parent_mapping, create_reverse_id_mapping

# PATH SETUP (do not change)
base_path = Path(__file__).parent.resolve()
allen2intfile = base_path / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = base_path / "files" / "CCF_v3_ontology.json"
custom_hier_path = base_path / "files"

#### USER INPUTS
# List of subject files (each representing one subject)
subject_files = [
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0290_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0291_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0292_counted_3d_cells.csv"),
    Path(r"Z:\Labmembers\Ingvild\RM1\example_analysis\CS0293_counted_3d_cells.csv"),
]

out_filename_prefix = "AverageDensity"  # Base name for saved plots
out_format = "tif"  # Desired output format
plot_title = "NeuN densities"

# Specify the parent region and hierarchy level you want to group by
specified_parent = "Isocortex"  # The parent region name to filter by
selected_hierarchy = "CustomLevel2_gm"  # Choose the hierarchy level (e.g. "CustomLevel1_gm", "CustomLevel2_gm")

# Prepare hierarchy information
id_mapping, color_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

# Create child-to-parent mapping for Allen ST level 5
child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

# Initialize all_densities as a dictionary to collect densities
all_densities = {}

# Process each subject file
for subject_file in subject_files:
    # Load the data for the current subject
    data_file = pd.read_csv(subject_file)
    data_file = data_file[data_file["ROI_Volume_mm_3"] != 0]

    # Create reverse mapping from 16-bit IDs to original IDs
    data_file = create_reverse_id_mapping(data_file, allen2intfile)

    # Collect densities for regions based on selected hierarchy and specified parent
    for region_id in hierarchy_regions.get(selected_hierarchy, []):
        parent_name = child_to_parent_dict.get(region_id, None)
        if parent_name == specified_parent:  # Check if this region's parent matches the specified parent
            # Check if the region_id exists in the data file
            matching_density_values = data_file.loc[data_file["ROI_id"] == region_id, "cell_density"]
            
            if not matching_density_values.empty:
                density_value = matching_density_values.values[0]
                
                # If the region_id is not yet in the dictionary, initialize it with an empty list
                if region_id not in all_densities:
                    all_densities[region_id] = []
                
                # Append the density value to the existing list
                all_densities[region_id].append(density_value)


# Create a reverse mapping from ID to name
id_to_name_mapping = {v: k for k, v in id_mapping.items()}

# Create list of region names based on ids
region_names = [id_to_name_mapping.get(region_id) for region_id in all_densities.keys()]
region_colors = [color_mapping.get(region_id) for region_id in all_densities.keys()]

# Calculate average densities and standard errors
avg_densities = [np.mean(all_densities[region_id]) for region_id in all_densities.keys()]
sem_densities = [np.std(all_densities[region_id]) / np.sqrt(len(all_densities[region_id])) for region_id in all_densities.keys()]

region_colors = [f"#{color}" for color in region_colors]

# Plotting
fig, ax = plt.subplots(figsize=(15, 8))
ax.bar(region_names, avg_densities, yerr=sem_densities, color=region_colors)

# Labeling the plot
ax.set_ylabel('Average Density', fontsize=16)
ax.set_title(plot_title, fontsize=20)
ax.set_xticklabels(region_names, rotation=45, ha='right', fontsize=12)

plt.tight_layout()

# Output path for plots
out_path = base_path / "plots"
out_path.mkdir(parents=True, exist_ok=True)

plt.savefig(out_path / f"{out_filename_prefix}_{specified_parent}.{out_format}")
plt.show()