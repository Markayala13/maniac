"""
Script para aplicar LUT cinematográfico a imágenes del hero
Preserva colores corporativos amarillos (#FFD400)
"""
import numpy as np
from PIL import Image
import os
import colorsys

# Rutas
LUT_PATH = r"E:\PROYECTOS\Maniacs\assets\luts\cinematic-tones-luts-pack-for-video-and-photo-2023-11-27-05-35-37-utc\Cinematic Tones_LUTs\Cinematic Tones 03.cube"
SLIDER_PATH = r"E:\PROYECTOS\Maniacs\plummet-plumber-and-construction-html-template-2024-11-20-07-49-25-utc\downloadable\plummet\assets\images\slider"
OUTPUT_PATH = r"E:\PROYECTOS\Maniacs\plummet-plumber-and-construction-html-template-2024-11-20-07-49-25-utc\downloadable\plummet\assets\img\hero\processed"

# Imágenes a procesar
IMAGES = ["latino.png", "slide2.png", "slide3.png"]

# Color corporativo amarillo (#FFD400) en HSV
CORPORATE_YELLOW_HUE = 48 / 360  # ~48 grados en HSV
YELLOW_HUE_TOLERANCE = 20 / 360  # Tolerancia de ±20 grados
YELLOW_SAT_MIN = 0.7  # Saturación mínima para considerar amarillo
YELLOW_VAL_MIN = 0.5  # Brillo mínimo


def read_cube_lut(filepath):
    """Lee un archivo .cube y retorna el LUT como array numpy"""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Encontrar tamaño del LUT
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
        raise ValueError("No se encontró LUT_3D_SIZE en el archivo")

    # Leer datos del LUT
    lut_data = []
    for line in lines[data_start:]:
        line = line.strip()
        if line and not line.startswith('#'):
            values = line.split()
            if len(values) == 3:
                lut_data.append([float(v) for v in values])

    # Convertir a array numpy y reshapear
    lut_array = np.array(lut_data, dtype=np.float32)
    lut_array = lut_array.reshape((size, size, size, 3))

    print(f"[OK] LUT cargado: {size}x{size}x{size}")
    return lut_array, size


def apply_lut_to_pixel(r, g, b, lut, size):
    """Aplica LUT a un pixel RGB usando interpolación trilineal"""
    # Normalizar RGB a [0, size-1]
    r_idx = r / 255.0 * (size - 1)
    g_idx = g / 255.0 * (size - 1)
    b_idx = b / 255.0 * (size - 1)

    # Índices inferiores
    r0 = int(np.floor(r_idx))
    g0 = int(np.floor(g_idx))
    b0 = int(np.floor(b_idx))

    # Índices superiores (con clipping)
    r1 = min(r0 + 1, size - 1)
    g1 = min(g0 + 1, size - 1)
    b1 = min(b0 + 1, size - 1)

    # Factores de interpolación
    r_frac = r_idx - r0
    g_frac = g_idx - g0
    b_frac = b_idx - b0

    # Interpolación trilineal (8 puntos del cubo)
    c000 = lut[r0, g0, b0]
    c001 = lut[r0, g0, b1]
    c010 = lut[r0, g1, b0]
    c011 = lut[r0, g1, b1]
    c100 = lut[r1, g0, b0]
    c101 = lut[r1, g0, b1]
    c110 = lut[r1, g1, b0]
    c111 = lut[r1, g1, b1]

    # Interpolación en R
    c00 = c000 * (1 - r_frac) + c100 * r_frac
    c01 = c001 * (1 - r_frac) + c101 * r_frac
    c10 = c010 * (1 - r_frac) + c110 * r_frac
    c11 = c011 * (1 - r_frac) + c111 * r_frac

    # Interpolación en G
    c0 = c00 * (1 - g_frac) + c10 * g_frac
    c1 = c01 * (1 - g_frac) + c11 * g_frac

    # Interpolación en B
    result = c0 * (1 - b_frac) + c1 * b_frac

    return result


def is_corporate_yellow(r, g, b):
    """Detecta si un pixel es del color amarillo corporativo"""
    # Convertir RGB a HSV
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)

    # Verificar si está en el rango del amarillo corporativo
    hue_min = CORPORATE_YELLOW_HUE - YELLOW_HUE_TOLERANCE
    hue_max = CORPORATE_YELLOW_HUE + YELLOW_HUE_TOLERANCE

    is_yellow = (hue_min <= h <= hue_max and
                 s >= YELLOW_SAT_MIN and
                 v >= YELLOW_VAL_MIN)

    return is_yellow


def is_black(r, g, b, threshold=50):
    """Detecta si un pixel es negro (para preservar negros del uniforme)"""
    return r < threshold and g < threshold and b < threshold


def apply_lut_to_image(image_path, lut, size, output_path):
    """Aplica LUT a una imagen preservando colores corporativos"""
    print(f"\nProcesando: {os.path.basename(image_path)}")

    # Cargar imagen
    img = Image.open(image_path)
    img_rgb = img.convert('RGB')
    img_array = np.array(img_rgb, dtype=np.float32)

    height, width = img_array.shape[:2]
    output_array = np.zeros_like(img_array)

    # Procesar cada pixel
    total_pixels = height * width
    yellow_preserved = 0
    black_preserved = 0

    for y in range(height):
        if y % 100 == 0:
            progress = (y * width) / total_pixels * 100
            print(f"  Progreso: {progress:.1f}%", end='\r')

        for x in range(width):
            r, g, b = img_array[y, x]

            # Verificar si es amarillo corporativo o negro
            if is_corporate_yellow(r, g, b):
                # Preservar amarillo corporativo (con ligero ajuste de contraste)
                output_array[y, x] = [r * 1.05, g * 1.05, b * 0.95]  # Boost amarillo
                yellow_preserved += 1
            elif is_black(r, g, b):
                # Preservar negros profundos
                output_array[y, x] = [r, g, b]
                black_preserved += 1
            else:
                # Aplicar LUT
                new_rgb = apply_lut_to_pixel(r, g, b, lut, size)
                output_array[y, x] = new_rgb * 255.0

    # Clip valores y convertir a uint8
    output_array = np.clip(output_array, 0, 255).astype(np.uint8)

    # Crear imagen de salida
    output_img = Image.fromarray(output_array, mode='RGB')

    # Guardar con optimización
    output_img.save(output_path, 'PNG', optimize=True, compress_level=6)

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  [OK] Guardado: {os.path.basename(output_path)} ({file_size_mb:.2f} MB)")
    print(f"    Amarillos preservados: {yellow_preserved:,} pixeles")
    print(f"    Negros preservados: {black_preserved:,} pixeles")

    return output_img


def main():
    print("=" * 60)
    print("APLICACION DE LUT CINEMATOGRAFICO")
    print("=" * 60)

    # Crear carpeta de salida
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    print(f"[OK] Carpeta de salida: {OUTPUT_PATH}")

    # Cargar LUT
    print(f"\nCargando LUT: Cinematic Tones 03")
    lut, size = read_cube_lut(LUT_PATH)

    # Procesar cada imagen
    for image_name in IMAGES:
        input_path = os.path.join(SLIDER_PATH, image_name)
        output_name = image_name.replace('.png', '_cinematic.png')
        output_path_full = os.path.join(OUTPUT_PATH, output_name)

        if os.path.exists(input_path):
            apply_lut_to_image(input_path, lut, size, output_path_full)
        else:
            print(f"[WARNING] No encontrado: {image_name}")

    print("\n" + "=" * 60)
    print("PROCESAMIENTO COMPLETADO")
    print("=" * 60)
    print(f"\nImagenes guardadas en:")
    print(f"   {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
