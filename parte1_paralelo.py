"""
============================================================
LABORATORIO IV - PARTE I: ALGORITMOS PARALELOS
Computación Paralela con ThreadPoolExecutor
============================================================
"""

import time
import random
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageFilter
import math


# ============================================================
# ACTIVIDAD 1.1: BÚSQUEDA PARALELA
# Divide un arreglo de 10M de datos en bloques y busca un objetivo
# ============================================================

def busqueda_en_bloque(args):
    """
    Busca el objetivo dentro de un bloque del arreglo.

    Parámetros:
        args (tuple): (bloque_id, subarreglo, objetivo)

    Retorna:
        int o None: Índice global si se encuentra, None si no.
    """
    bloque_id, subarreglo, objetivo, offset = args
    for i, valor in enumerate(subarreglo):
        if valor == objetivo:
            return offset + i  # Índice global real
    return None


def busqueda_paralela(arreglo, objetivo, num_hilos):
    """
    Búsqueda lineal paralela sobre un arreglo de gran tamaño.

    Estrategia: divide el arreglo en `num_hilos` bloques iguales
    y cada hilo busca en su bloque de forma concurrente.

    Parámetros:
        arreglo  (list): Arreglo de enteros con 10 millones de datos.
        objetivo (int) : Valor a buscar.
        num_hilos (int): Número de hilos (2, 4 u 8).

    Retorna:
        int o None: Primera posición encontrada, o None si no existe.
    """
    n = len(arreglo)
    tam_bloque = math.ceil(n / num_hilos)

    # Construir lista de tareas: (id_bloque, subarreglo, objetivo, offset)
    tareas = []
    for i in range(num_hilos):
        inicio = i * tam_bloque
        fin    = min(inicio + tam_bloque, n)
        tareas.append((i, arreglo[inicio:fin], objetivo, inicio))

    resultado = None

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        futuros = {executor.submit(busqueda_en_bloque, t): t for t in tareas}

        for futuro in as_completed(futuros):
            pos = futuro.result()
            if pos is not None:
                if resultado is None or pos < resultado:
                    resultado = pos   # Guardamos la posición más pequeña

    return resultado


def demo_busqueda():
    """Ejecuta la búsqueda con 2, 4 y 8 hilos y mide tiempos."""
    print("=" * 60)
    print("ACTIVIDAD 1.1 — BÚSQUEDA PARALELA")
    print("=" * 60)

    TAM = 10_000_000
    print(f"Generando arreglo de {TAM:,} enteros aleatorios...")
    arreglo  = [random.randint(0, TAM) for _ in range(TAM)]
    objetivo = arreglo[random.randint(0, TAM - 1)]   # Garantizamos que existe
    print(f"Objetivo: {objetivo}\n")

    # Búsqueda secuencial de referencia
    t0 = time.perf_counter()
    pos_seq = next((i for i, v in enumerate(arreglo) if v == objetivo), None)
    t_seq   = time.perf_counter() - t0
    print(f"Secuencial          → pos={pos_seq}  tiempo={t_seq:.4f}s")

    for hilos in (2, 4, 8):
        t0  = time.perf_counter()
        pos = busqueda_paralela(arreglo, objetivo, hilos)
        t   = time.perf_counter() - t0
        speedup = t_seq / t if t > 0 else float('inf')
        print(f"Paralelo ({hilos} hilos)  → pos={pos}  tiempo={t:.4f}s  speedup={speedup:.2f}x")

    print()


# ============================================================
# ACTIVIDAD 1.2: PROCESAMIENTO DE IMAGEN PARALELO
# Convierte a escala de grises y aplica Blur por regiones
# ============================================================

def convertir_region_grises(args):
    """
    Convierte una región rectangular de la imagen a escala de grises.

    Parámetros:
        args (tuple): (imagen_array, fila_inicio, fila_fin)

    Retorna:
        tuple: (fila_inicio, region_grises_array)
    """
    img_array, fila_inicio, fila_fin = args
    region = img_array[fila_inicio:fila_fin, :, :]          # Recortar región
    # Fórmula estándar de luminancia (ITU-R BT.601)
    grises = (0.299 * region[:, :, 0] +
              0.587 * region[:, :, 1] +
              0.114 * region[:, :, 2]).astype(np.uint8)
    return (fila_inicio, grises)


def aplicar_blur_region(args):
    """
    Aplica un filtro Gaussian Blur a una región de la imagen.

    Parámetros:
        args (tuple): (imagen_pil_region, fila_inicio)

    Retorna:
        tuple: (fila_inicio, imagen_pil_blur)
    """
    img_region, fila_inicio = args
    blur = img_region.filter(ImageFilter.GaussianBlur(radius=3))
    return (fila_inicio, blur)


def procesar_imagen_paralelo(ruta_imagen, num_hilos=4):
    """
    Procesa una imagen en paralelo aplicando:
        1. Conversión a escala de grises (por regiones horizontales)
        2. Filtro Gaussian Blur                (por regiones horizontales)

    Parámetros:
        ruta_imagen (str): Ruta a la imagen de entrada.
        num_hilos   (int): Número de hilos a utilizar.

    Retorna:
        tuple: (imagen_grises PIL, imagen_blur PIL)
    """
    img      = Image.open(ruta_imagen).convert("RGB")
    img_arr  = np.array(img)
    alto, ancho, _ = img_arr.shape
    tam_bloque = math.ceil(alto / num_hilos)

    # ── Paso 1: Escala de grises en paralelo ────────────────────
    tareas_grises = [
        (img_arr,
         i * tam_bloque,
         min((i + 1) * tam_bloque, alto))
        for i in range(num_hilos)
    ]

    resultado_grises = np.zeros((alto, ancho), dtype=np.uint8)

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        for fila_inicio, region in executor.map(convertir_region_grises,
                                                tareas_grises):
            fin = fila_inicio + region.shape[0]
            resultado_grises[fila_inicio:fin, :] = region

    img_grises = Image.fromarray(resultado_grises, mode="L")

    # ── Paso 2: Gaussian Blur en paralelo ───────────────────────
    tareas_blur = [
        (img_grises.crop((0,
                          i * tam_bloque,
                          ancho,
                          min((i + 1) * tam_bloque, alto))),
         i * tam_bloque)
        for i in range(num_hilos)
    ]

    img_blur_final = Image.new("L", (ancho, alto))

    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        for fila_inicio, region_blur in executor.map(aplicar_blur_region,
                                                     tareas_blur):
            img_blur_final.paste(region_blur, (0, fila_inicio))

    return img_grises, img_blur_final


def demo_imagen():
    """Crea una imagen sintética y aplica el procesamiento paralelo."""
    print("=" * 60)
    print("ACTIVIDAD 1.2 — PROCESAMIENTO DE IMAGEN PARALELO")
    print("=" * 60)

    # Crear imagen sintética de 800×600 con degradado de colores
    ancho, alto = 800, 600
    datos = np.zeros((alto, ancho, 3), dtype=np.uint8)
    for y in range(alto):
        for x in range(ancho):
            datos[y, x] = [x % 256, y % 256, (x + y) % 256]
    img_sintetica = Image.fromarray(datos, "RGB")
    img_sintetica.save("/tmp/imagen_entrada.png")
    print("Imagen sintética 800×600 creada en /tmp/imagen_entrada.png")

    for hilos in (2, 4, 8):
        t0 = time.perf_counter()
        grises, blur = procesar_imagen_paralelo("/tmp/imagen_entrada.png",
                                                num_hilos=hilos)
        t = time.perf_counter() - t0
        grises.save(f"/tmp/grises_{hilos}hilos.png")
        blur.save(f"/tmp/blur_{hilos}hilos.png")
        print(f"{hilos} hilos → tiempo={t:.4f}s  "
              f"(grises + blur guardados en /tmp/)")

    print()


# ============================================================
# ACTIVIDAD 1.3: ESTADÍSTICAS PARALELAS
# Min, Max, Suma y Promedio de 5M de datos por bloques
# ============================================================

def estadisticas_bloque(args):
    """
    Calcula estadísticas parciales sobre un bloque de datos.

    Parámetros:
        args (tuple): (id_bloque, subarreglo numpy)

    Retorna:
        dict: {min, max, suma, count} del bloque.
    """
    _, bloque = args
    return {
        "min"  : float(np.min(bloque)),
        "max"  : float(np.max(bloque)),
        "suma" : float(np.sum(bloque)),
        "count": len(bloque),
    }


def calcular_estadisticas_paralelo(datos, num_hilos):
    """
    Calcula min, max, suma y promedio de un arreglo grande en paralelo.

    Estrategia: divide los datos en `num_hilos` bloques iguales,
    cada hilo calcula estadísticas parciales y luego se combinan.

    Parámetros:
        datos     (np.ndarray): Arreglo de 5 millones de flotantes.
        num_hilos (int)       : Número de hilos (2, 4 u 8).

    Retorna:
        dict: {min, max, suma, promedio}
    """
    n = len(datos)
    tam_bloque = math.ceil(n / num_hilos)

    tareas = [
        (i, datos[i * tam_bloque: min((i + 1) * tam_bloque, n)])
        for i in range(num_hilos)
    ]

    parciales = []
    with ThreadPoolExecutor(max_workers=num_hilos) as executor:
        parciales = list(executor.map(estadisticas_bloque, tareas))

    # Combinar resultados parciales
    global_min  = min(p["min"]  for p in parciales)
    global_max  = max(p["max"]  for p in parciales)
    global_suma = sum(p["suma"] for p in parciales)
    global_n    = sum(p["count"] for p in parciales)

    return {
        "min"     : global_min,
        "max"     : global_max,
        "suma"    : global_suma,
        "promedio": global_suma / global_n,
    }


def demo_estadisticas():
    """Ejecuta estadísticas paralelas con 2, 4 y 8 hilos."""
    print("=" * 60)
    print("ACTIVIDAD 1.3 — ESTADÍSTICAS PARALELAS")
    print("=" * 60)

    TAM = 5_000_000
    print(f"Generando arreglo numpy de {TAM:,} flotantes...")
    datos = np.random.uniform(0, 1_000_000, size=TAM)

    # Referencia secuencial con numpy
    t0     = time.perf_counter()
    ref    = {"min": float(np.min(datos)), "max": float(np.max(datos)),
              "suma": float(np.sum(datos)), "promedio": float(np.mean(datos))}
    t_seq  = time.perf_counter() - t0
    print(f"\nSecuencial (numpy)  → min={ref['min']:.2f}  max={ref['max']:.2f}"
          f"  prom={ref['promedio']:.2f}  tiempo={t_seq:.4f}s")

    for hilos in (2, 4, 8):
        t0  = time.perf_counter()
        est = calcular_estadisticas_paralelo(datos, hilos)
        t   = time.perf_counter() - t0
        speedup = t_seq / t if t > 0 else float('inf')
        print(f"Paralelo ({hilos} hilos)  → min={est['min']:.2f}  "
              f"max={est['max']:.2f}  prom={est['promedio']:.2f}  "
              f"tiempo={t:.4f}s  speedup={speedup:.2f}x")

    print()


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    demo_busqueda()
    demo_imagen()
    demo_estadisticas()
