import pandas as pd
import json
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import nibabel as nib
import cv2
from PIL import Image

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

def format_custom_regions(file, id_mapping):
    # Read Excel file
    read_file = pd.read_excel(file)
    regions = read_file.columns.tolist()
    regions.remove("Custom brain region")
    if "root" in regions:
        regions.remove("root")

    region_ids = []
    for name in regions:
        # Find the ID corresponding to the name
        region_id = [key for key, value in id_mapping.items() if value == name]  # Check by name
        if region_id:  # If found
            region_ids.append(region_id[0])  # Append the first matched ID
    
    return region_ids

def prepare_hierarchy_info(hierarchy_file, custom_hier_path):
    with open(hierarchy_file, 'r') as file:
        json_data = json.load(file)

    # Map 'id' to 'name'
    id_mapping = get_mappings(json_data, 'id', 'name')  
    color_mapping = get_mappings(json_data, 'id', 'color_hex_triplet')
    acronym_mapping = get_mappings(json_data, 'id', 'acronym')

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

    hierarchy_paths = {name: custom_hier_path / f"{name}.xlsx" for name in hierarchy_names}

    hierarchy_regions = {
        name: format_custom_regions(path, id_mapping) 
        for name, path in hierarchy_paths.items()
    }
    
    return id_mapping, color_mapping, acronym_mapping, hierarchy_regions

def create_child_to_parent_mapping(custom_hier_path, hierarchy_name):
    """Create child-to-parent mapping from Allen ST level hierarchy Excel."""
    grouping_data = pd.read_excel(custom_hier_path / f"{hierarchy_name}.xlsx")
    grouping_data = grouping_data.drop(index=grouping_data.index[0])  # Drop the first row
    grouping_data = grouping_data.drop(columns=grouping_data.columns[0])  # Drop the first column
    child_to_parent_dict = {}

    # Create child-to-parent mapping
    for parent_region in grouping_data.columns:
        children = grouping_data[parent_region].dropna()
        for child in children:
            child_to_parent_dict[child] = parent_region

    return child_to_parent_dict

def create_reverse_id_mapping(allen2intfile):
    """Create a reverse mapping from 16-bit IDs (used by Kim lab) to original IDs."""
    # Create reverse mapping from 16-bit ids to original ids
    allen2int = pd.read_excel(allen2intfile)
    allen2int_dict = dict(zip(allen2int.iloc[:, 0], allen2int.iloc[:, 1]))
    reverse_id_mapping = {v: k for k, v in allen2int_dict.items()}

    return reverse_id_mapping

def load_and_prepare_data(file_path, allen2intfile, reverse=True):
    # Load the data for the current subject
    data_file = pd.read_csv(file_path)

    if reverse == True:
        # Create reverse mapping from 16-bit IDs to original IDs
        reverse_id_mapping = create_reverse_id_mapping(allen2intfile)
        
        # Create a copy of the data_file with original IDs
        #data_file_allen_ids = data_file.copy()
        data_file['ROI_id'] = data_file['ROI_id'].map(reverse_id_mapping).fillna(data_file['ROI_id'])

    return data_file


def collect_values_directly(data_file, values_column, region_list, id_mapping):

    all_values = {}

    for region in region_list:
        region_id = [key for key, val in id_mapping.items() if val == region]
        region_id = region_id[0]
        volume_value = data_file.loc[data_file["ROI_id"] == region_id, "ROI_Volume_mm_3"].values[0]

        if volume_value != 0:
            value = data_file.loc[data_file["ROI_id"] == region_id, values_column].values[0]
            all_values[region_id] = value
    
    return all_values


def collect_values_by_hierarchy(data_file, values_column, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent=""):
    all_values = {}

    if specified_parent:
        for region_id in hierarchy_regions.get(selected_hierarchy, []):
            parent_name = child_to_parent_dict.get(region_id, None)
            volume_value = data_file.loc[data_file["ROI_id"] == region_id, "ROI_Volume_mm_3"].values[0]
            if parent_name == specified_parent and volume_value != 0:
                value = data_file.loc[data_file["ROI_id"] == region_id, values_column].values[0]
                all_values[region_id] = value
            else:
                continue
    else:
        for region_id in hierarchy_regions.get(selected_hierarchy, []):
            volume_value = data_file.loc[data_file["ROI_id"] == region_id, "ROI_Volume_mm_3"].values[0]
            if volume_value != 0:
                value = data_file.loc[data_file["ROI_id"] == region_id, values_column].values[0]
                all_values[region_id] = value

    return all_values

def average_value_dicts(dict_list):
    # Initialize dictionaries to hold the sums, counts, and sums of squares
    sums = {}
    counts = {}
    sums_of_squares = {}

    # Iterate through each dictionary in the list
    for d in dict_list:
        for key, value in d.items():
            # Accumulate sums and counts
            if key in sums:
                sums[key] += value
                counts[key] += 1
                sums_of_squares[key] += value ** 2
            else:
                sums[key] = value
                counts[key] = 1
                sums_of_squares[key] = value ** 2

    # Initialize dictionaries for averages and standard errors
    averages = {}
    standard_errors = {}

    # Calculate averages and standard errors
    for key in sums:
        averages[key] = sums[key] / counts[key]
        # Calculate variance and standard error
        variance = (sums_of_squares[key] / counts[key]) - (averages[key] ** 2)
        standard_deviation = variance ** 0.5
        standard_errors[key] = standard_deviation / (counts[key] ** 0.5)

    return averages, standard_errors


def normalize_value_values(value_dict_list):
    all_value_values = [value for d in value_dict_list for value in d.values()]

    min_value = np.nanmin(all_value_values)
    max_value = np.nanmax(all_value_values)
    
    # Use min-max normalization
    normalized_dicts_list = []
    for d in value_dict_list:
        normalized_dict = {}
        for key, value in d.items():
            normalized = (value - min_value) / (max_value - min_value) if max_value > min_value else value
            normalized_dict[key] = normalized

        normalized_dicts_list.append(normalized_dict)
    
    return normalized_dicts_list

def prepare_groupwise_values_dict(IDs_to_files_dict, grouping, value_column, allen2intfile, selected_hierarchy, specified_parent,
                                  hierarchy_regions, custom_hier_path, parent_hierarchy_level, id_mapping, region_list = [], reverse=True):
    # Prepare individual value data
    all_individual_values = {}  # Store individual values in a dictionary of dictionaries for each group

    for ID, file in IDs_to_files_dict.items():
        ID_group = grouping.get(ID)
        data_file = load_and_prepare_data(file, allen2intfile, reverse)
        
        child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, parent_hierarchy_level)

        if region_list:
            values_in_file = collect_values_directly(data_file, value_column, region_list, id_mapping)

        else:
            # Collect the values
            values_in_file = collect_values_by_hierarchy(data_file, value_column, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent)

        for region_id, value in values_in_file.items():
            if region_id not in all_individual_values:
                all_individual_values[region_id] = {}
            if ID_group not in all_individual_values[region_id]:
                all_individual_values[region_id][ID_group] = []
            all_individual_values[region_id][ID_group].append(value)

    return all_individual_values

def get_descriptive_stats(all_individual_values):
    """Calculates average values and standard errors for each group."""
    avg_values_to_group_dict = {}
    se_to_region_group_dict = {}
    n_to_group_dict = {}
    
    for region, group_values in all_individual_values.items():
        avg_values_to_group_dict[region] = {}
        se_to_region_group_dict[region] = {}
        
        for group, values in group_values.items():
            n = len(values)
            if n > 0:
                mean_value = np.mean(values)
                se_value = np.std(values, ddof=1) / np.sqrt(n)  # Standard Error Calculation
                
                avg_values_to_group_dict[region][group] = mean_value
                se_to_region_group_dict[region][group] = se_value
                n_to_group_dict[group] = n
            else:
                # Signal that no data is available
                avg_values_to_group_dict[region][group] = np.nan  # Use NaN to indicate missing data
                se_to_region_group_dict[region][group] = np.nan

    return avg_values_to_group_dict, se_to_region_group_dict, n_to_group_dict


def perform_t_tests(all_individual_values, group1_name, group2_name):
    """Perform t-tests between two specified groups for all regions and return a dictionary with significance levels."""
    significant_results = {}  # Dictionary to hold significance results

    for region in all_individual_values.keys():
        group1_data = all_individual_values[region].get(group1_name, [])
        group2_data = all_individual_values[region].get(group2_name, [])

        if group1_data and group2_data:  # Proceed only if both groups have data
            t_stat, p_value = stats.ttest_ind(group1_data, group2_data)
            if p_value < 0.001:
                significant_results[region] = '***'
            elif p_value < 0.01:
                significant_results[region] = '**'
            elif p_value < 0.05:
                significant_results[region] = '*'
            else:
                significant_results[region] = None  # Not significant

    return significant_results

def add_bracket(ax, x_range, y_pos=1.05, line_width=2):
    start, end = x_range
    ax.annotate('', xy=(start, y_pos), xytext=(end, y_pos),
                arrowprops=dict(arrowstyle='-', lw=line_width, color='black'),
                annotation_clip=False, xycoords=('data', 'axes fraction'), textcoords=('data', 'axes fraction'))

def create_barplot(save_path, region_names, values, region_colors, parent_labels, plot_title, value_name,
                   group_labels=False, yerr=None, selected_hierarchy="FullHierarchy", specified_parent=None, rotation=45, 
                   ha='right', fontsize_labels=16, fontsize_titles=20, figsize=(35, 15)):
    
    # Plot the data
    fig, ax = plt.subplots(figsize=figsize)

    ax.bar(region_names, values, yerr=yerr, color=region_colors)
    ax.set_ylabel(value_name, fontsize=fontsize_labels)
    ax.set_title(plot_title, fontsize=fontsize_titles)
    ax.set_xticklabels(region_names, rotation=rotation, ha=ha, fontsize=fontsize_labels)

    # Grouping the x-axis
    if selected_hierarchy in ["CustomLevel1_gm", "CustomLevel2_gm", "CustomLevel3_gm", "FullHierarchy"] and specified_parent is None:
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
    plt.savefig(save_path)
    plt.show()


def create_groupwise_barplot(save_path, region_names, id_mapping, avg_values_to_region_dict,
                              se_to_region_group_dict, significant_results, groups, n_to_group_dict,
                              region_colors, plot_title, hatch_patterns, value_name):
    """Plots a bar chart of average values across regions with error bars."""
    
    num_groups = len(groups)

    # Make graph wider if there are more than two groups
    extra_groups = num_groups - 2

    x = np.arange(len(region_names))  # The label locations
    width = 0.4 - (extra_groups * 0.15)  # The width of the bars
    group_space = 0.1  # Space between groups of bars
    fig_width = 12 + (extra_groups + 8)

    fig, ax = plt.subplots(figsize=(fig_width, 7))  # Adjust figure size as necessary

    # Loop through groups to draw bars
    for i, group in enumerate(groups):
        # Adjust bar positions to ensure they are spaced correctly
        bar_positions = x + i * (width + group_space)  # Shift bars over for each group
        bar_values = [avg_values_to_region_dict.get(region, {}).get(group, 0) for region in region_names]
        y_errors = [se_to_region_group_dict.get(region, {}).get(group, 0) for region in region_names]
        
        # Set hatch pattern for the bars
        hatch = hatch_patterns[i % len(hatch_patterns)]  

        # Create bars
        ax.bar(bar_positions, bar_values, width, yerr=y_errors,
               label=f"{group}, n = {n_to_group_dict.get(group)}", 
               color=region_colors, hatch=hatch)

    # Annotate significant differences with asterisks and draw brackets
    for j, region in enumerate(region_names):
        if region in significant_results and significant_results[region] is not None:
            # Calculate the x-coordinate for the bracket
            start_x = j - (width + group_space) * 0.1  # Adjust for spacing
            end_x = j + (width + group_space)

            # Find the maximum error height for the current bars
            max_bar_value = max(avg_values_to_region_dict[region].get(group, 0) for group in groups)
            max_error = max([se_to_region_group_dict[region].get(g, 0) for g in groups]) if region in se_to_region_group_dict else 0
            y_bracket = max(max_bar_value + max_error, 0) + 0.1 * max_bar_value  # Position for the bracket

            # Draw the bracket
            ax.plot([start_x, end_x], [y_bracket, y_bracket], color='black', lw=1.5)  # Draw the bracket

            # Annotate significance level above the bracket
            ax.annotate(significant_results[region], 
                        xy=((start_x + end_x) / 2, y_bracket + 0.05),  # Centered above the bracket
                        fontsize=12, ha='center')

    # Finalize the plot
    ax.set_xlabel('Regions')
    ax.set_ylabel(value_name)
    ax.set_title(plot_title)
    
    # Center the x-ticks in relation to the bars
    ax.set_xticks(x + (num_groups - 1) * (width + group_space) / 2)  
    ax.set_xticklabels([id_mapping.get(region) for region in region_names], rotation=45, ha='right')
    ax.legend()

    # Save and show the plot
    plt.tight_layout()
    plt.savefig(save_path)  # Save as per your specified path
    plt.show()  # Show the plot




def hex_to_rgb(hex_color):
    """Convert a hex color string to an RGB tuple."""
    hex_color = str(hex_color)
    hex_color = hex_color.lstrip('#')  # Remove '#' if present
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b

def atlas_to_svg(atlas_plate, color_mapping, filename):
    height, width = atlas_plate.shape[:2]

    masks = {}
    
    # Create a binary mask for each ID
    for id_value in np.unique(atlas_plate):
        if id_value in color_mapping:  # Only consider IDs that have color mapping
            mask = (atlas_plate == id_value).astype(np.uint8)  # Create binary mask
            masks[id_value] = mask

    with open(filename, 'w') as svg_file:
        svg_file.write(f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g>\n""")

        for id_value, mask in masks.items():
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Get the fill color from the color mapping
            hex_color = color_mapping.get(id_value, '#000000')
            r, g, b = hex_to_rgb(hex_color)

            for contour in contours:
                # Prepare SVG path data
                path_string = 'M '  # Initialize the path string
                for point in contour[:, 0]:  # Contour is an array of points (x, y)
                    x, y = point
                    path_string += f"{x} {y} "  # Keep y as is
                path_string += 'Z'  # Close the path
                
                # Write the path to the SVG file with black outline
                svg_file.write(f'    <path d="{path_string}" fill="rgb({r},{g},{b})" stroke="black" stroke-width="1" />\n')

        svg_file.write("  </g>\n</svg>")

def convert_colors(orig_image, color_mapping):
    height, width = orig_image.shape
    color_image = np.zeros((height, width, 3), dtype=np.uint8)  

    for i in range(height):
        for j in range(width):
            id_value = orig_image[i, j]

            # Get the color corresponding to the ID from the mapping
            hex_color = color_mapping.get(id_value, '#000000')  # Default to black if ID not found
            r, g, b = hex_to_rgb(hex_color)

            # Assign the RGB color to the color image
            color_image[i, j] = [r, g, b]
    return color_image

def create_grayscale_mapping(roi_id, atlas_plate, color_mapping):
    # Find all unique IDs in the atlas, excluding ROI ID and background ID (0)
    unique_ids = np.unique(atlas_plate)
    ids_to_convert = unique_ids[(unique_ids != roi_id) & (unique_ids != 0)]  # Use boolean indexing

    # Create a mapping for unique to lighter grayscale hex values
    num_ids = len(ids_to_convert)

    # Assign lighter grayscale values for each ID
    light_gray_shades = np.linspace(110, 230, num_ids, dtype=np.uint8)

    # Create a mapping dictionary with hex values for correspondingly unique IDs
    grayscale_mapping = {roi_id: color_mapping.get(roi_id)}  # Start with the ROI ID mapping

    # Using dictionary comprehension to assign the grayscale values to each unique ID
    grayscale_mapping.update({
        int(id_value): f"#{gray_value:02x}{gray_value:02x}{gray_value:02x}" 
        for id_value, gray_value in zip(ids_to_convert, light_gray_shades)
    })

    return grayscale_mapping

