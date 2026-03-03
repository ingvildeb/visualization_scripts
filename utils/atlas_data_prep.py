import json

import pandas as pd


def get_mappings(data, key_property, value_property, default_value=None):
    mapping = {}

    def recursive_collect(node):
        key = node.get(key_property)
        value = node.get(value_property, default_value)
        if key is not None and value is not None:
            mapping[key] = value

        for child in node.get("children", []):
            recursive_collect(child)

    for entry in data["msg"]:
        recursive_collect(entry)

    return mapping


def format_custom_regions(file, id_mapping):
    read_file = pd.read_excel(file)
    regions = read_file.columns.tolist()
    regions.remove("Custom brain region")
    if "root" in regions:
        regions.remove("root")

    region_ids = []
    for name in regions:
        region_id = [key for key, value in id_mapping.items() if value == name]
        if region_id:
            region_ids.append(region_id[0])

    return region_ids


def prepare_hierarchy_info(hierarchy_file, custom_hier_path):
    with open(hierarchy_file, "r") as file:
        json_data = json.load(file)

    id_mapping = get_mappings(json_data, "id", "name")
    color_mapping = get_mappings(json_data, "id", "color_hex_triplet")
    acronym_mapping = get_mappings(json_data, "id", "acronym")

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
        "FullHierarchy",
    ]

    hierarchy_paths = {name: custom_hier_path / f"{name}.xlsx" for name in hierarchy_names}

    hierarchy_regions = {name: format_custom_regions(path, id_mapping) for name, path in hierarchy_paths.items()}

    return id_mapping, color_mapping, acronym_mapping, hierarchy_regions


def create_child_to_parent_mapping(custom_hier_path, hierarchy_name):
    grouping_data = pd.read_excel(custom_hier_path / f"{hierarchy_name}.xlsx")
    grouping_data = grouping_data.drop(index=grouping_data.index[0])
    grouping_data = grouping_data.drop(columns=grouping_data.columns[0])
    child_to_parent_dict = {}

    for parent_region in grouping_data.columns:
        children = grouping_data[parent_region].dropna()
        for child in children:
            child_to_parent_dict[child] = parent_region

    return child_to_parent_dict


def create_reverse_id_mapping(allen2intfile):
    allen2int = pd.read_excel(allen2intfile)
    allen2int_dict = dict(zip(allen2int.iloc[:, 0], allen2int.iloc[:, 1]))
    reverse_id_mapping = {v: k for k, v in allen2int_dict.items()}
    return reverse_id_mapping


def load_and_prepare_data(file_path, allen2intfile, reverse=True):
    data_file = pd.read_csv(file_path)

    if reverse is True:
        reverse_id_mapping = create_reverse_id_mapping(allen2intfile)
        data_file["ROI_id"] = data_file["ROI_id"].map(reverse_id_mapping).fillna(data_file["ROI_id"])

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


def collect_values_by_hierarchy(
    data_file, values_column, hierarchy_regions, selected_hierarchy, child_to_parent_dict, specified_parent=""
):
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


def prepare_groupwise_values_dict(
    ids_to_files_dict,
    grouping,
    value_column,
    allen2intfile,
    selected_hierarchy,
    specified_parent,
    hierarchy_regions,
    custom_hier_path,
    parent_hierarchy_level,
    id_mapping,
    region_list=[],
    reverse=True,
):
    all_individual_values = {}

    for sample_id, file in ids_to_files_dict.items():
        id_group = grouping.get(sample_id)
        data_file = load_and_prepare_data(file, allen2intfile, reverse)

        child_to_parent_dict = create_child_to_parent_mapping(custom_hier_path, parent_hierarchy_level)

        if region_list:
            values_in_file = collect_values_directly(data_file, value_column, region_list, id_mapping)
        else:
            values_in_file = collect_values_by_hierarchy(
                data_file,
                value_column,
                hierarchy_regions,
                selected_hierarchy,
                child_to_parent_dict,
                specified_parent,
            )

        for region_id, value in values_in_file.items():
            if region_id not in all_individual_values:
                all_individual_values[region_id] = {}
            if id_group not in all_individual_values[region_id]:
                all_individual_values[region_id][id_group] = []
            all_individual_values[region_id][id_group].append(value)

    return all_individual_values
