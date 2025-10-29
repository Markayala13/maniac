"""
Script para aplicar TODOS los LUTs disponibles y comparar
"""
import numpy as np
from PIL import Image
import os
import colorsys

# Rutas
LUTS_FOLDER = r"E:\PROYECTOS\Maniacs\assets\luts\cinematic-tones-luts-pack-for-video-and-photo-2023-11-27-05-35-37-utc\Cinematic Tones_LUTs"
SLIDER_PATH = r"E:\PROYECTOS\Maniacs\plummet-plumber-and-construction-html-template-2024-11-20-07-49-25-utc\downloadable\plummet\assets\images\slider"
OUTPUT_BASE = r"E:\PROYECTOS\Maniacs\plummet-plumber-and-construction-html-template-2024-11-20-07-49-25-utc\downloadable\plummet\assets\img\hero"

# Imágenes a procesar
IMAGES = ["latino.png", "slide2.png", "slide3.png"]

# LUTs a probar
LUTS = ["Cinematic Tones 02.cube", "Cinematic Tones 04.cube", "Cinematic Tones 05.cube"]

# Color corporativo amarillo
CORPORATE_YELLOW_HUE = 48 / 360
YELLOW_HUE_TOLERANCE = 20 / 360
YELLOW_SAT_MIN = 0.7
YELLOW_VAL_MIN = 0.5


def read_cube_lut(filepath):
    """Lee un archivo .cube y retorna el LUT como array numpy"""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    size = None
    data_start = 0

    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('LUT_3D_SIZE'):
            size = int(line.split()[-1])
        elif not line.startswith('#') and not line.startswith('TITLE') and not line.startswith('LUT_3D_SIZE') and line:
            data_start = i
            break

    if size is None:
        raise ValueError("No se encontro LUT_3D_SIZE")

    lut_data = []
    for line in lines[data_start:]:
        line = line.strip()
        if line and not line.startswith('#'):
            values = line.split()
            if len(values) == 3:
                lut_data.append([float(v) for v in values])

    lut_array = np.array(lut_data, dtype=np.float32)
    lut_array = lut_array.reshape((size, size, size, 3))

    return lut_array, size


def apply_lut_to_pixel(r, g, b, lut, size):
    """Aplica LUT a un pixel RGB"""
    r_idx = r / 255.0 * (size - 1)
    g_idx = g / 255.0 * (size - 1)
    b_idx = b / 255.0 * (size - 1)

    r0 = int(np.floor(r_idx))
    g0 = int(np.floor(g_idx))
    b0 = int(np.floor(b_idx))

    r1 = min(r0 + 1, size - 1)
    g1 = min(g0 + 1, size - 1)
    b1 = min(b0 + 1, size - 1)

    r_frac = r_idx - r0
    g_frac = g_idx - g0
    b_frac = b_idx - b0

    c000 = lut[r0, g0, b0]
    c001 = lut[r0, g0, b1]
    c010 = lut[r0, g1, b0]
    c011 = lut[r0, g1, b1]
    c100 = lut[r1, g0, b0]
    c101 = lut[r1, g0, b1]
    c110 = lut[r1, g1, b0]
    c111 = lut[r1, g1, b1]

    c00 = c000 * (1 - r_frac) + c100 * r_frac
    c01 = c001 * (1 - r_frac) + c101 * r_frac
    c10 = c010 * (1 - r_frac) + c110 * r_frac
    c11 = c011 * (1 - r_frac) + c111 * r_frac

    c0 = c00 * (1 - g_frac) + c10 * g_frac
    c1 = c01 * (1 - g_frac) + c11 * g_frac

    result = c0 * (1 - b_frac) + c1 * b_frac

    return result


def is_corporate_yellow(r, g, b):
    """Detecta amarillo corporativo"""
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
    hue_min = CORPORATE_YELLOW_HUE - YELLOW_HUE_TOLERANCE
    hue_max = CORPORATE_YELLOW_HUE + YELLOW_HUE_TOLERANCE
    return (hue_min <= h <= hue_max and s >= YELLOW_SAT_MIN and v >= YELLOW_VAL_MIN)


def is_black(r, g, b, threshold=50):
    """Detecta negros"""
    return r < threshold and g < threshold and b < threshold


def apply_lut_to_image(image_path, lut, size, output_path):
    """Aplica LUT preservando colores corporativos"""
    img = Image.open(image_path)
    img_rgb = img.convert('RGB')
    img_array = np.array(img_rgb, dtype=np.float32)

    height, width = img_array.shape[:2]
    output_array = np.zeros_like(img_array)

    for y in range(height):
        if y % 100 == 0:
            progress = (y * width) / (height * width) * 100
            print(f"  Progreso: {progress:.1f}%", end='\r')

        for x in range(width):
            r, g, b = img_array[y, x]

            if is_corporate_yellow(r, g, b):
                output_array[y, x] = [r * 1.05, g * 1.05, b * 0.95]
            elif is_black(r, g, b):
                output_array[y, x] = [r, g, b]
            else:
                new_rgb = apply_lut_to_pixel(r, g, b, lut, size)
                output_array[y, x] = new_rgb * 255.0

    output_array = np.clip(output_array, 0, 255).astype(np.uint8)
    output_img = Image.fromarray(output_array, mode='RGB')
    output_img.save(output_path, 'PNG', optimize=True, compress_level=6)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  [OK] Guardado: {os.path.basename(output_path)} ({file_size_mb:.2f} MB)")

    return output_img


def main():
    print("=" * 60)
    print("PROCESANDO TODOS LOS LUTS DISPONIBLES")
    print("=" * 60)

    # Procesar cada LUT
    for lut_name in LUTS:
        lut_number = lut_name.split()[2].replace('.cube', '')
        print(f"\n>>> PROCESANDO LUT {lut_number}")

        lut_path = os.path.join(LUTS_FOLDER, lut_name)
        output_folder = os.path.join(OUTPUT_BASE, f"lut{lut_number}")
        os.makedirs(output_folder, exist_ok=True)

        print(f"Cargando: {lut_name}")
        lut, size = read_cube_lut(lut_path)
        print(f"[OK] LUT {lut_number} cargado: {size}x{size}x{size}")

        # Procesar cada imagen
        for image_name in IMAGES:
            input_path = os.path.join(SLIDER_PATH, image_name)
            output_name = image_name.replace('.png', f'_lut{lut_number}.png')
            output_path_full = os.path.join(output_folder, output_name)

            if os.path.exists(input_path):
                print(f"\nProcesando: {image_name} -> LUT {lut_number}")
                apply_lut_to_image(input_path, lut, size, output_path_full)

    print("\n" + "=" * 60)
    print("PROCESAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"\nImagenes guardadas en:")
    print(f"   {OUTPUT_BASE}\\lut02\\")
    print(f"   {OUTPUT_BASE}\\lut04\\")
    print(f"   {OUTPUT_BASE}\\lut05\\")


if __name__ == "__main__":
    main()
