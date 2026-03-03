import sys
from pathlib import Path

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import load_script_config, normalize_user_path
from utils.utils import (
    create_groupwise_barplot,
    get_descriptive_stats,
    perform_t_tests,
    prepare_groupwise_values_dict,
    prepare_hierarchy_info,
)


def resolve_config_path(path_like: str | Path, script_dir: Path) -> Path:
    p = normalize_user_path(path_like)
    return p if p.is_absolute() else (script_dir / p).resolve()


def resolve_value_name(value_column: str) -> str:
    if value_column == "cell_density":
        return "Density"
    if value_column == "cell_counted":
        return "Cell number"
    if value_column == "ROI_Volume_mm_3":
        return "Region volume"
    return value_column


script_path = Path(__file__).resolve()
script_dir = script_path.parent
test_mode = True
cfg = load_script_config(script_path, "barplots_per_group", test_mode=test_mode)

ids_to_files_dict = {k: resolve_config_path(v, script_dir) for k, v in cfg["ids_to_files"].items()}
grouping = dict(cfg["grouping"])
value_column = cfg["value_column"]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg.get("specified_parent")
if specified_parent in ("", "None", "none", False):
    specified_parent = None
parent_hierarchy_level = cfg["parent_hierarchy_level"]
region_list = cfg.get("region_list", [])
out_filename_prefix = cfg["out_filename_prefix"]
out_path = resolve_config_path(cfg["out_path"], script_dir)
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
apply_t_test = bool(cfg["apply_t_test"])
hatch_patterns = list(cfg["hatch_patterns"])
id_system = cfg["id_system"]
error_metric = str(cfg.get("error_metric", "se")).lower()
error_mode = cfg.get("error_mode", None)
if error_mode is None:
    # Backward compatibility for older configs.
    show_error_bars = bool(cfg.get("show_error_bars", False))
    error_mode = "both" if show_error_bars else "dots"
jitter_frac = float(cfg.get("jitter_frac", 0.0))

repo_root = script_dir.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}.{out_format}"
else:
    save_path = out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}.{out_format}"

groups = list(dict.fromkeys(grouping.values()))
value_name = resolve_value_name(value_column)

id_mapping, color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

if id_system == "KimLab16bit":
    all_individual_values = prepare_groupwise_values_dict(
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
        region_list,
        reverse=True,
    )
elif id_system == "OriginalAllen":
    all_individual_values = prepare_groupwise_values_dict(
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
        region_list,
        reverse=False,
    )
else:
    raise RuntimeError("ID system not recognized. Must be KimLab16bit or OriginalAllen")

avg_values_to_region_dict, error_to_region_group_dict, n_to_group_dict = get_descriptive_stats(
    all_individual_values,
    error_metric=error_metric,
)

if apply_t_test and len(groups) > 2:
    print(f"Not able to apply t-test for n = {len(groups)} groups. Consider another statistical test.")
    apply_t_test = False

significant_results = {region: None for region in avg_values_to_region_dict.keys()}
if apply_t_test:
    significant_results = perform_t_tests(all_individual_values, groups[0], groups[1])

create_groupwise_barplot(
    save_path,
    list(avg_values_to_region_dict.keys()),
    {region: id_mapping[region] for region in avg_values_to_region_dict.keys()},
    avg_values_to_region_dict,
    error_to_region_group_dict,
    significant_results,
    groups,
    n_to_group_dict,
    [f"#{color_mapping.get(region)}" for region in avg_values_to_region_dict.keys()],
    plot_title,
    hatch_patterns,
    value_name,
    all_individual_values=all_individual_values,
    error_mode=error_mode,
    jitter_frac=jitter_frac,
)
