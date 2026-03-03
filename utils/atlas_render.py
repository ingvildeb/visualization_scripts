import cv2
import numpy as np


def hex_to_rgb(hex_color):
    hex_color = str(hex_color)
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def atlas_to_svg(atlas_plate, color_mapping, filename):
    height, width = atlas_plate.shape[:2]

    masks = {}

    for id_value in np.unique(atlas_plate):
        if id_value in color_mapping:
            mask = (atlas_plate == id_value).astype(np.uint8)
            masks[id_value] = mask

    with open(filename, "w") as svg_file:
        svg_file.write(
            f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <g>\n"""
        )

        for id_value, mask in masks.items():
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            hex_color = color_mapping.get(id_value, "#000000")
            r, g, b = hex_to_rgb(hex_color)

            for contour in contours:
                path_string = "M "
                for point in contour[:, 0]:
                    x, y = point
                    path_string += f"{x} {y} "
                path_string += "Z"

                svg_file.write(
                    f'    <path d="{path_string}" fill="rgb({r},{g},{b})" stroke="black" stroke-width="1" />\n'
                )

        svg_file.write("  </g>\n</svg>")


def convert_colors(orig_image, color_mapping):
    height, width = orig_image.shape
    color_image = np.zeros((height, width, 3), dtype=np.uint8)

    for i in range(height):
        for j in range(width):
            id_value = orig_image[i, j]
            hex_color = color_mapping.get(id_value, "#000000")
            r, g, b = hex_to_rgb(hex_color)
            color_image[i, j] = [r, g, b]
    return color_image


def create_grayscale_mapping(roi_id, atlas_plate, color_mapping):
    unique_ids = np.unique(atlas_plate)
    ids_to_convert = unique_ids[(unique_ids != roi_id) & (unique_ids != 0)]
    num_ids = len(ids_to_convert)
    light_gray_shades = np.linspace(110, 230, num_ids, dtype=np.uint8)

    grayscale_mapping = {roi_id: color_mapping.get(roi_id)}
    grayscale_mapping.update(
        {
            int(id_value): f"#{gray_value:02x}{gray_value:02x}{gray_value:02x}"
            for id_value, gray_value in zip(ids_to_convert, light_gray_shades)
        }
    )

    return grayscale_mapping
