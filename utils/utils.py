import pandas as pd
import json
import numpy as np
from scipy import stats
import cv2


def metric_to_label(value_column):
    mapping = {
        "cell_density": "Density",
        "cell_counted": "Cell number",
        "ROI_Volume_mm_3": "Region volume",
    }
    return mapping.get(value_column, value_column)


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

def average_value_dicts(dict_list, error_metric="se", return_all_error_metrics=False):
    error_metric = str(error_metric).lower()
    if error_metric not in {"se", "sd"}:
        raise ValueError("error_metric must be 'se' or 'sd'")

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

    # Initialize dictionaries for averages and error metrics
    averages = {}
    standard_deviations = {}
    standard_errors = {}

    # Calculate averages and error metrics
    for key in sums:
        averages[key] = sums[key] / counts[key]
        n = counts[key]
        if n > 1:
            variance = (sums_of_squares[key] - (sums[key] ** 2) / n) / (n - 1)
            variance = max(variance, 0.0)
            standard_deviation = variance ** 0.5
        else:
            standard_deviation = 0.0
        standard_error = standard_deviation / (n ** 0.5)

        standard_deviations[key] = standard_deviation
        standard_errors[key] = standard_error

    selected_error = standard_errors if error_metric == "se" else standard_deviations
    if return_all_error_metrics:
        return averages, selected_error, standard_deviations, standard_errors
    return averages, selected_error


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

def get_descriptive_stats(all_individual_values, error_metric="se", return_all_error_metrics=False):
    """Calculate average values plus SD/SE for each group."""
    error_metric = str(error_metric).lower()
    if error_metric not in {"se", "sd"}:
        raise ValueError("error_metric must be 'se' or 'sd'")

    avg_values_to_group_dict = {}
    se_to_region_group_dict = {}
    sd_to_region_group_dict = {}
    n_to_group_dict = {}
    
    for region, group_values in all_individual_values.items():
        avg_values_to_group_dict[region] = {}
        se_to_region_group_dict[region] = {}
        sd_to_region_group_dict[region] = {}
        
        for group, values in group_values.items():
            n = len(values)
            if n > 0:
                mean_value = np.mean(values)
                sd_value = np.std(values, ddof=1) if n > 1 else 0.0
                se_value = sd_value / np.sqrt(n)
                
                avg_values_to_group_dict[region][group] = mean_value
                sd_to_region_group_dict[region][group] = sd_value
                se_to_region_group_dict[region][group] = se_value
                n_to_group_dict[group] = n
            else:
                # Signal that no data is available
                avg_values_to_group_dict[region][group] = np.nan  # Use NaN to indicate missing data
                sd_to_region_group_dict[region][group] = np.nan
                se_to_region_group_dict[region][group] = np.nan

    error_to_region_group_dict = se_to_region_group_dict if error_metric == "se" else sd_to_region_group_dict

    if return_all_error_metrics:
        return (
            avg_values_to_group_dict,
            error_to_region_group_dict,
            n_to_group_dict,
            sd_to_region_group_dict,
            se_to_region_group_dict,
        )

    return avg_values_to_group_dict, error_to_region_group_dict, n_to_group_dict


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

