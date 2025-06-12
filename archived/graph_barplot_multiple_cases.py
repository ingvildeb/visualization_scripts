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
    # Add more subject files as needed
]

out_filename_prefix = "AverageDensity"  # Base name for saved plots
out_format = "tif"  # Desired output format
hierarchy = "CustomLevel2_gm"  # Hierarchy choice
plot_title = "NeuN densities"

# Prepare hierarchy information
id_mapping, color_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

# Create child-to-parent mapping for Allen ST level 5
child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, "Allen_STlevel_5")

# Prepare to collect densities and names
all_densities = {region_id: [] for region_id in hierarchy_regions.get(hierarchy, [])}

# Process each subject file
for subject_file in subject_files:
    # Load the data for the current subject
    data_file = pd.read_csv(subject_file)

    # Create reverse mapping from 16-bit IDs to original IDs
    data_file = create_reverse_id_mapping(data_file, allen2intfile)
    
    # Collect densities for each region by region ID
    for region_id in hierarchy_regions.get(hierarchy, []):
        density = data_file.loc[data_file["ROI_id"] == region_id, "cell_density"].values[0]
        all_densities[region_id].append(density)

# Create a reverse mapping from ID to name
id_to_name_mapping = {v: k for k, v in id_mapping.items()}

# Create list of region names based on ids
region_names = [id_to_name_mapping.get(region_id) for region_id in all_densities.keys()]
region_colors = [color_mapping.get(region_id) for region_id in all_densities.keys()]

# Prepare to find parent names
parent_labels = [child_to_parent_dict.get(region_id, '') for region_id in all_densities.keys()]

# Calculate average densities and standard errors
avg_densities = [np.mean(all_densities[region_id]) for region_id in all_densities.keys()]
sem_densities = [np.std(all_densities[region_id]) / np.sqrt(len(all_densities[region_id])) for region_id in all_densities.keys()]

region_colors = [f"#{color}" for color in region_colors]

# Plotting
fig, ax = plt.subplots(figsize=(50, 15))
ax.bar(region_names, avg_densities, yerr=sem_densities, color=region_colors)

ax.set_ylabel('Density', fontsize=16)
ax.set_title(plot_title, fontsize=20)
ax.set_xticklabels(region_names, rotation=45, ha='right', fontsize=16)

# Grouping the x-axis
if hierarchy in ["CustomLevel1_gm", "CustomLevel2_gm", "CustomLevel3_gm", "FullHierarchy"]:
    # Hide the main x-axis labels
    ax.set_xticklabels([])
    ax.tick_params(axis='x', which='both', bottom=False, top=False)

    # Create a secondary x-axis for the parent groups
    sec_ax = ax.secondary_xaxis('bottom')
    sec_ax.tick_params(axis='x', which='both', bottom=False, top=False)

    unique_parents = list(dict.fromkeys(parent_labels))
    group_boundaries = []
    group_positions = []
    parent_names = []

    for parent in unique_parents:
        indices = [i for i, x in enumerate(parent_labels) if x == parent]
        if indices:
            start_index, end_index = indices[0], indices[-1]
            group_boundaries.append((start_index, end_index))
            group_positions.append((start_index + end_index) / 2)
        
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
out_path.mkdir(parents=True, exist_ok=True)

plt.savefig(out_path / f"{out_filename_prefix}_{hierarchy}.{out_format}")
plt.show()
