import numpy as np
from scipy import stats


def metric_to_label(value_column):
    mapping = {
        "cell_density": "Density",
        "cell_counted": "Cell number",
        "ROI_Volume_mm_3": "Region volume",
    }
    return mapping.get(value_column, value_column)


def average_value_dicts(dict_list, error_metric="se", return_all_error_metrics=False):
    error_metric = str(error_metric).lower()
    if error_metric not in {"se", "sd"}:
        raise ValueError("error_metric must be 'se' or 'sd'")

    sums = {}
    counts = {}
    sums_of_squares = {}

    for d in dict_list:
        for key, value in d.items():
            if key in sums:
                sums[key] += value
                counts[key] += 1
                sums_of_squares[key] += value**2
            else:
                sums[key] = value
                counts[key] = 1
                sums_of_squares[key] = value**2

    averages = {}
    standard_deviations = {}
    standard_errors = {}

    for key in sums:
        averages[key] = sums[key] / counts[key]
        n = counts[key]
        if n > 1:
            variance = (sums_of_squares[key] - (sums[key] ** 2) / n) / (n - 1)
            variance = max(variance, 0.0)
            standard_deviation = variance**0.5
        else:
            standard_deviation = 0.0
        standard_error = standard_deviation / (n**0.5)

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

    normalized_dicts_list = []
    for d in value_dict_list:
        normalized_dict = {}
        for key, value in d.items():
            normalized = (value - min_value) / (max_value - min_value) if max_value > min_value else value
            normalized_dict[key] = normalized

        normalized_dicts_list.append(normalized_dict)

    return normalized_dicts_list


def get_descriptive_stats(all_individual_values, error_metric="se", return_all_error_metrics=False):
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
                avg_values_to_group_dict[region][group] = np.nan
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
    significant_results = {}

    for region in all_individual_values.keys():
        group1_data = all_individual_values[region].get(group1_name, [])
        group2_data = all_individual_values[region].get(group2_name, [])

        if group1_data and group2_data:
            _t_stat, p_value = stats.ttest_ind(group1_data, group2_data)
            if p_value < 0.001:
                significant_results[region] = "***"
            elif p_value < 0.01:
                significant_results[region] = "**"
            elif p_value < 0.05:
                significant_results[region] = "*"
            else:
                significant_results[region] = None

    return significant_results
