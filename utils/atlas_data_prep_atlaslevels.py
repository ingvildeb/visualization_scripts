import pandas as pd

from atlaslevels import (
    convert_dataframe_ids,
    load_preset_bundle,
    load_preset_id_map,
    load_preset_ontology,
)


SUPPORTED_GM_LEVELS = {
    "CustomLevel1_gm",
    "CustomLevel2_gm",
    "CustomLevel3_gm",
    "CustomLevel4_gm",
    "CustomLevel5_gm",
    "CustomLevel6_gm",
    "CustomLevel7_gm",
}


def load_allen_gm_context():
    ontology = load_preset_ontology("allen_ccfv3")
    bundle = load_preset_bundle("allen_gm")
    return ontology, bundle


def build_ontology_mappings(ontology):
    id_mapping = {node_id: node.name for node_id, node in ontology.nodes.items()}
    color_mapping = {node_id: node.color.lstrip("#") for node_id, node in ontology.nodes.items()}
    acronym_mapping = {node_id: node.acronym for node_id, node in ontology.nodes.items()}
    return id_mapping, color_mapping, acronym_mapping


def prepare_hierarchy_info_atlaslevels():
    ontology, bundle = load_allen_gm_context()
    id_mapping, color_mapping, acronym_mapping = build_ontology_mappings(ontology)
    hierarchy_regions = {
        level_name: bundle.get_selected_region_ids(level_name)
        for level_name in SUPPORTED_GM_LEVELS
    }
    return ontology, bundle, id_mapping, color_mapping, acronym_mapping, hierarchy_regions


def load_and_prepare_data(file_path, allen2intfile, reverse=True):
    data_file = pd.read_csv(file_path)

    if reverse:
        reverse_id_map = load_preset_id_map("allen_ccfv3_allen_to_kimlab16bit").invert()
        data_file = convert_dataframe_ids(data_file, "ROI_id", reverse_id_map, copy=False)

    return data_file


def collect_values_directly(data_file, values_column, region_ids):
    all_values = {}

    for region_id in region_ids:
        row = data_file.loc[data_file["ROI_id"] == region_id]
        if row.empty:
            continue

        volume_value = row["ROI_Volume_mm_3"].values[0]
        if volume_value != 0:
            all_values[region_id] = row[values_column].values[0]

    return all_values


def resolve_region_list(ontology, region_list):
    resolved = []
    for region in region_list:
        resolved.append(ontology.resolve_name(region) if isinstance(region, str) else region)
    return resolved


def collect_values_by_hierarchy_atlaslevels(
    data_file,
    values_column,
    bundle,
    selected_hierarchy,
    specified_parent="",
):
    all_values = {}
    selected_ids = bundle.get_selected_region_ids(selected_hierarchy)
    specified_parent_id = None

    if specified_parent:
        specified_parent_id = bundle.ontology.resolve_name(specified_parent)
        if specified_parent_id in selected_ids:
            raise ValueError(
                f"specified_parent '{specified_parent}' is itself included in {selected_hierarchy}. "
                "specified_parent must be coarser than the selected hierarchy."
            )

    for region_id in selected_ids:
        row = data_file.loc[data_file["ROI_id"] == region_id]
        if row.empty:
            continue

        volume_value = row["ROI_Volume_mm_3"].values[0]
        if volume_value == 0:
            continue

        if specified_parent_id is not None and not bundle.ontology.is_ancestor(specified_parent_id, region_id):
            continue

        all_values[region_id] = row[values_column].values[0]

    return all_values


def build_parent_label_mapping(bundle, selected_hierarchy, parent_hierarchy_level):
    if parent_hierarchy_level not in SUPPORTED_GM_LEVELS:
        raise ValueError(
            "For the atlaslevels-backed migration path, parent_hierarchy_level must be one of the GM levels: "
            f"{sorted(SUPPORTED_GM_LEVELS)}"
        )

    mapping = {}
    for region_id in bundle.get_selected_region_ids(selected_hierarchy):
        mapped_parent = bundle.map_region_to_level_parent(region_id, parent_hierarchy_level)
        mapping[region_id] = bundle.ontology.get_name(mapped_parent) if mapped_parent is not None else None
    return mapping


def prepare_groupwise_values_dict_atlaslevels(
    ids_to_files_dict,
    grouping,
    value_column,
    allen2intfile,
    selected_hierarchy,
    specified_parent,
    region_list=None,
    reverse=True,
):
    ontology, bundle = load_allen_gm_context()
    all_individual_values = {}
    region_list = region_list or []
    resolved_region_list = resolve_region_list(ontology, region_list) if region_list else []

    for sample_id, file in ids_to_files_dict.items():
        id_group = grouping.get(sample_id)
        data_file = load_and_prepare_data(file, allen2intfile, reverse)

        if resolved_region_list:
            values_in_file = collect_values_directly(data_file, value_column, resolved_region_list)
        else:
            values_in_file = collect_values_by_hierarchy_atlaslevels(
                data_file=data_file,
                values_column=value_column,
                bundle=bundle,
                selected_hierarchy=selected_hierarchy,
                specified_parent=specified_parent,
            )

        for region_id, value in values_in_file.items():
            if region_id not in all_individual_values:
                all_individual_values[region_id] = {}
            if id_group not in all_individual_values[region_id]:
                all_individual_values[region_id][id_group] = []
            all_individual_values[region_id][id_group].append(value)

    return all_individual_values, bundle
