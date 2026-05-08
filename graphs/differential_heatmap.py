import math
import sys
from pathlib import Path

import altair as alt
import pandas as pd

parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from utils.io_helpers import (
    load_script_config,
    normalize_user_path,
    require_absolute_path,
    require_file,
)
from utils.atlas_data_prep import prepare_groupwise_values_dict, prepare_hierarchy_info
from utils.stats import get_descriptive_stats


def ordered_unique(values):
    out = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


def percent_change(group_average, control_average, minimum_control_value):
    if group_average is None or control_average is None:
        return math.nan
    if pd.isna(group_average) or pd.isna(control_average):
        return math.nan
    if abs(control_average) <= minimum_control_value:
        return math.nan
    return ((group_average - control_average) / control_average) * 100


def format_metric_label(metric):
    if metric == "percent_change":
        return "% change from control"
    return metric


def numeric_domain(values, include_zero=False):
    numeric_values = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if numeric_values.empty:
        return [0, 1]

    min_value = float(numeric_values.min())
    max_value = float(numeric_values.max())
    if include_zero:
        min_value = min(min_value, 0)
        max_value = max(max_value, 0)

    if min_value == max_value:
        padding = abs(min_value) * 0.1 if min_value else 1
        min_value -= padding
        max_value += padding

    return [min_value, max_value]


def change_color_domain(values, mode, fixed_percent):
    if mode == "symmetric_fixed":
        if fixed_percent <= 0:
            raise RuntimeError("change_color_domain_percent must be > 0")
        return [-fixed_percent, fixed_percent]

    if mode == "symmetric_data":
        domain = numeric_domain(values, include_zero=True)
        max_abs = max(abs(domain[0]), abs(domain[1]))
        if max_abs == 0:
            max_abs = 1
        return [-max_abs, max_abs]

    raise RuntimeError("change_color_domain_mode must be 'symmetric_fixed' or 'symmetric_data'")


def legend_only_chart(field, title, scale, domain, gradient_length, legend_offset):
    return (
        alt.Chart(pd.DataFrame({field: domain}))
        .mark_point(opacity=0)
        .encode(
            color=alt.Color(
                f"{field}:Q",
                scale=scale,
                title=title,
                legend=alt.Legend(
                    orient="right",
                    gradientLength=gradient_length,
                    offset=legend_offset,
                ),
            )
        )
        .properties(width=1, height=1)
    )


def validate_config(
    groups,
    control_group,
    differential_metric,
    control_display,
    zero_control_policy,
    control_minimum_for_percent_change,
):
    if control_group not in groups:
        raise RuntimeError(
            f"control_group must match one of the configured groups. Got {control_group!r}; "
            f"available groups are: {groups}"
        )
    if differential_metric != "percent_change":
        raise RuntimeError("differential_metric currently supports only 'percent_change'")
    if control_display not in {"raw", "zero"}:
        raise RuntimeError("control_display must be 'raw' or 'zero'")
    if zero_control_policy != "nan":
        raise RuntimeError("zero_control_policy currently supports only 'nan'")
    if control_minimum_for_percent_change < 0:
        raise RuntimeError("control_minimum_for_percent_change must be >= 0")


# -------------------------
# CONFIG LOADING
# -------------------------
script_path = Path(__file__).resolve()
test_mode = False
cfg = load_script_config(script_path, "differential_heatmap", test_mode=test_mode)

# -------------------------
# CONFIG PARAMETERS
# -------------------------
ids_to_files_dict = {
    k: require_file(
        require_absolute_path(normalize_user_path(v), f"Input file for {k}"),
        f"Input file for {k}",
    )
    for k, v in cfg["ids_to_files"].items()
}
grouping = dict(cfg["grouping"])
value_column = cfg["value_column"]
selected_hierarchy = cfg["selected_hierarchy"]
specified_parent = cfg["specified_parent"]
parent_hierarchy_level = cfg["parent_hierarchy_level"]
region_list = cfg["region_list"]
out_filename_prefix = cfg["out_filename_prefix"]
out_path = require_absolute_path(normalize_user_path(cfg["out_path"]), "Output directory")
out_format = cfg["out_format"]
plot_title = cfg["plot_title"]
x_axis_title = cfg["x_axis_title"]
orientation = cfg["orientation"]
id_system = cfg["id_system"]
error_metric = cfg["error_metric"]

control_group = cfg["control_group"]
differential_metric = cfg.get("differential_metric", "percent_change")
include_control = cfg.get("include_control", True)
control_display = cfg.get("control_display", "raw")
zero_control_policy = cfg.get("zero_control_policy", "nan")
control_minimum_for_percent_change = float(cfg.get("control_minimum_for_percent_change", 0))
change_color_scheme = cfg.get("change_color_scheme", "redblue")
change_color_reverse = cfg.get("change_color_reverse", True)
change_color_domain_mode = cfg.get("change_color_domain_mode", "symmetric_fixed")
change_color_domain_percent = float(cfg.get("change_color_domain_percent", 50))
control_color_scheme = cfg.get("control_color_scheme", "viridis")
legend_gradient_length = cfg.get("legend_gradient_length", 120)
legend_offset = cfg.get("legend_offset", 8)
legend_stack_spacing = cfg.get("legend_stack_spacing", 28)
legend_chart_spacing = cfg.get("legend_chart_spacing", 12)
group_cell_width = cfg.get("group_cell_width", 90)
group_cell_height = cfg.get("group_cell_height", 35)

# -------------------------
# PATHS
# -------------------------
repo_root = script_path.parent.parent
allen2intfile = repo_root / "files" / "CCFv3_OntologyStructure_u16.xlsx"
hierarchy_file = repo_root / "files" / "CCF_v3_ontology.json"
custom_hier_path = repo_root / "files"
out_path.mkdir(parents=True, exist_ok=True)

if specified_parent:
    save_path = (
        out_path
        / f"{out_filename_prefix}_{selected_hierarchy}_{specified_parent}_{value_column}_{control_group}_{differential_metric}_{orientation}.{out_format}"
    )
else:
    save_path = (
        out_path / f"{out_filename_prefix}_{selected_hierarchy}_{value_column}_{control_group}_{differential_metric}_{orientation}.{out_format}"
    )

# -------------------------
# MAIN
# -------------------------
groups = ordered_unique(grouping.values())
validate_config(
    groups,
    control_group,
    differential_metric,
    control_display,
    zero_control_policy,
    control_minimum_for_percent_change,
)

id_mapping, _color_mapping, _acronym_mapping, hierarchy_regions = prepare_hierarchy_info(hierarchy_file, custom_hier_path)

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

avg_values_to_group_dict, error_to_region_group_dict, _n_to_group_dict = get_descriptive_stats(
    all_individual_values,
    error_metric=error_metric,
)
error_label = "SE" if error_metric == "se" else "SD"
change_label = format_metric_label(differential_metric)

region_ids = list(avg_values_to_group_dict.keys())
region_labels = [id_mapping.get(region, region) for region in region_ids]
diff_groups = [group for group in groups if group != control_group]
if include_control and control_display == "zero":
    diff_groups = groups

control_data = []
diff_data = []
for region in region_ids:
    region_label = id_mapping.get(region, region)
    control_average = avg_values_to_group_dict.get(region, {}).get(control_group, math.nan)
    control_error = error_to_region_group_dict.get(region, {}).get(control_group, math.nan)

    if include_control and control_display == "raw":
        control_data.append(
            {
                "Region": region_label,
                "Group": control_group,
                "Control average": control_average,
                error_label: control_error,
            }
        )

    for group in diff_groups:
        group_average = avg_values_to_group_dict.get(region, {}).get(group, math.nan)
        error_value = error_to_region_group_dict.get(region, {}).get(group, math.nan)
        change_value = percent_change(group_average, control_average, control_minimum_for_percent_change)
        diff_data.append(
            {
                "Region": region_label,
                "Group": group,
                "Control average": control_average,
                "Group average": group_average,
                change_label: change_value,
                error_label: error_value,
            }
        )

control_df = pd.DataFrame(control_data)
diff_df = pd.DataFrame(diff_data)
control_domain = numeric_domain(control_df["Control average"] if not control_df.empty else [])
change_domain = change_color_domain(
    diff_df[change_label] if not diff_df.empty else [],
    change_color_domain_mode,
    change_color_domain_percent,
)
control_scale = alt.Scale(scheme=control_color_scheme, domain=control_domain)
change_scale = alt.Scale(
    scheme=change_color_scheme,
    domain=change_domain,
    domainMid=0,
    reverse=change_color_reverse,
)
legend_column = alt.vconcat(
    legend_only_chart(
        "Control average",
        "Control average",
        control_scale,
        control_domain,
        legend_gradient_length,
        legend_offset,
    ),
    legend_only_chart(
        change_label,
        change_label,
        change_scale,
        change_domain,
        legend_gradient_length,
        legend_offset,
    ),
    spacing=legend_stack_spacing,
).resolve_scale(color="independent")

change_tooltip = [
    alt.Tooltip("Region:N"),
    alt.Tooltip("Group:N"),
    alt.Tooltip("Control average:Q", format=".3f"),
    alt.Tooltip("Group average:Q", format=".3f"),
    alt.Tooltip(f"{change_label}:Q", format=".2f"),
    alt.Tooltip(f"{error_label}:Q", format=".3f"),
]
control_tooltip = [
    alt.Tooltip("Region:N"),
    alt.Tooltip("Group:N"),
    alt.Tooltip("Control average:Q", format=".3f"),
    alt.Tooltip(f"{error_label}:Q", format=".3f"),
]

if orientation == "vertical":
    diff_heatmap = (
        alt.Chart(diff_df)
        .mark_rect()
        .encode(
            x=alt.X("Group:O", title=None, sort=diff_groups),
            y=alt.Y("Region:O", sort=region_labels, title=None),
            color=alt.Color(
                f"{change_label}:Q",
                scale=change_scale,
                title=change_label,
                legend=alt.Legend(gradientLength=legend_gradient_length),
            ),
            tooltip=change_tooltip,
        )
        .properties(width=group_cell_width * len(diff_groups))
    )

    if include_control and control_display == "raw":
        diff_heatmap = diff_heatmap.encode(
            y=alt.Y(
                "Region:O",
                sort=region_labels,
                axis=alt.Axis(labels=False, ticks=False, title=None),
            ),
            color=alt.Color(
                f"{change_label}:Q",
                scale=change_scale,
                title=change_label,
                legend=None,
            ),
        )
        control_heatmap = (
            alt.Chart(control_df)
            .mark_rect()
            .encode(
                x=alt.X("Group:O", title=None, sort=[control_group]),
                y=alt.Y("Region:O", sort=region_labels, title=None),
                color=alt.Color(
                    "Control average:Q",
                    scale=control_scale,
                    title="Control average",
                    legend=None,
                ),
                tooltip=control_tooltip,
            )
            .properties(width=group_cell_width)
        )
        heatmap_body = (
            alt.hconcat(control_heatmap, diff_heatmap, spacing=0, bounds="flush")
            .resolve_scale(color="independent")
        )
        heatmap = (
            alt.hconcat(legend_column, heatmap_body, spacing=legend_chart_spacing)
            .resolve_scale(color="independent")
            .configure_axis(labelLimit=200)
        )
    else:
        heatmap = diff_heatmap.configure_axis(labelLimit=200)

    heatmap.save(str(save_path))
    heatmap.display()
elif orientation == "horizontal":
    diff_heatmap = (
        alt.Chart(diff_df)
        .mark_rect()
        .encode(
            x=alt.X(
                "Region:O",
                title=None,
                sort=region_labels,
                axis=alt.Axis(labelFontSize=12, titleFontSize=14, labelAngle=45),
            ),
            y=alt.Y(
                "Group:O",
                title=None,
                sort=diff_groups,
                axis=alt.Axis(labelFontSize=12, titleFontSize=14),
            ),
            color=alt.Color(
                f"{change_label}:Q",
                scale=change_scale,
                title=change_label,
                legend=alt.Legend(gradientLength=legend_gradient_length),
            ),
            tooltip=change_tooltip,
        )
        .properties(width=1000, height=group_cell_height * len(diff_groups))
    )

    if include_control and control_display == "raw":
        diff_heatmap = diff_heatmap.encode(
            x=alt.X(
                "Region:O",
                sort=region_labels,
                axis=None,
            ),
            y=alt.Y(
                "Group:O",
                title=None,
                sort=diff_groups,
                axis=alt.Axis(labelFontSize=12, titleFontSize=14),
            ),
            color=alt.Color(
                f"{change_label}:Q",
                scale=change_scale,
                title=change_label,
                legend=None,
            ),
        )
        control_heatmap = (
            alt.Chart(control_df)
            .mark_rect()
            .encode(
                x=alt.X(
                    "Region:O",
                    title=None,
                    sort=region_labels,
                    axis=alt.Axis(labelFontSize=12, titleFontSize=14, labelAngle=45, orient="top"),
                ),
                y=alt.Y(
                    "Group:O",
                    title=None,
                    sort=[control_group],
                    axis=alt.Axis(labelFontSize=12, titleFontSize=14),
                ),
                color=alt.Color(
                    "Control average:Q",
                    scale=control_scale,
                    title="Control average",
                    legend=None,
                ),
                tooltip=control_tooltip,
            )
            .properties(width=1000, height=group_cell_height)
        )
        heatmap_body = (
            alt.vconcat(control_heatmap, diff_heatmap, spacing=0, bounds="flush")
            .resolve_scale(color="independent")
        )
        heatmap = (
            alt.hconcat(legend_column, heatmap_body, spacing=legend_chart_spacing)
            .resolve_scale(color="independent")
            .configure_axis(labelLimit=300)
        )
    else:
        heatmap = diff_heatmap.configure_axis(labelLimit=300)

    heatmap.save(str(save_path))
    heatmap.display()
else:
    raise RuntimeError("orientation must be 'vertical' or 'horizontal'")
