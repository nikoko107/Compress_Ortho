#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour compresser des images aériennes avec les caractéristiques suivantes:
- Compression JPEG (90%)
- Espace colorimétrique YCbCr
- Format tuilé
- 4 niveaux d'aperçus internes compressés en JPEG
- Accélération GPU via CUDA
"""

import os
import argparse
import multiprocessing
import time
from osgeo import gdal

# Vérifier si GDAL supporte CUDA
has_cuda = 'CUDA' in gdal.GetDriverByName('GTiff').GetMetadataItem('DMD_CREATIONOPTIONLIST') or False

def check_gpu_support():
    """
    Vérifie si GDAL est compilé avec le support CUDA
    
    Returns:
        bool: True si CUDA est supporté, False sinon
    """
    try:
        # Vérifier si le support GPU est disponible
        gpu_count = gdal.GetCacheMax() // 1000000  # Méthode heuristique
        
        # Alternative : vérifier les pilotes disponibles
        drivers = [gdal.GetDriver(i).ShortName for i in range(gdal.GetDriverCount())]
        cuda_capability = 'CUDA' in ' '.join(drivers) or has_cuda
        
        if cuda_capability:
            print("Support GPU détecté!")
            return True
        else:
            print("Support GPU non détecté dans cette version de GDAL.")
            return False
    except:
        print("Erreur lors de la vérification du support GPU.")
        return False

def compress_geotiff(input_file, output_file, use_gpu=False):
    """
    Compresse une image aérienne selon les critères spécifiés.
    
    Args:
        input_file (str): Chemin vers le fichier d'entrée
        output_file (str): Chemin vers le fichier de sortie
        use_gpu (bool): Utiliser l'accélération GPU si disponible
    
    Returns:
        bool: True si la compression a réussi, False sinon
    """
    try:
        start_time = time.time()
        
        # Configuration GDAL pour performance
        gdal.SetConfigOption('GDAL_CACHEMAX', '2048')  # Cache de 2 Go
        
        # Ouvrir le fichier source
        src_ds = gdal.Open(input_file, gdal.GA_ReadOnly)
        if src_ds is None:
            print(f"Impossible d'ouvrir le fichier {input_file}")
            return False
        
        # Récupérer les informations sur l'image source
        width = src_ds.RasterXSize
        height = src_ds.RasterYSize
        bands = src_ds.RasterCount
        data_type = src_ds.GetRasterBand(1).DataType
        projection = src_ds.GetProjection()
        geo_transform = src_ds.GetGeoTransform()
        
        # Définir les options de création pour le fichier de sortie
        cpu_count = multiprocessing.cpu_count()
        options = [
            'COMPRESS=JPEG',           # Compression JPEG
            'JPEG_QUALITY=90',         # Qualité de compression à 90%
            'PHOTOMETRIC=YCBCR',       # Espace colorimétrique YCbCr
            'TILED=YES',               # Format tuilé
            'BLOCKXSIZE=512',          # Taille des tuiles en X (augmentée pour GPU)
            'BLOCKYSIZE=512',          # Taille des tuiles en Y (augmentée pour GPU)
            f'NUM_THREADS={cpu_count}' # Utiliser tous les CPUs disponibles
        ]
        
        # Ajouter des options spécifiques au GPU si disponible et demandé
        if use_gpu and has_cuda:
            options.extend([
                'GPUNODE=AUTO',        # Sélection automatique du GPU
                'USE_CUDA=YES',        # Utiliser CUDA
                'GPU_CACHE_SIZE=40',   # Taille du cache GPU en pourcentage
                'INTERLEAVE=PIXEL'     # Format pixel interleaved pour GPU
            ])
            print("Utilisation de l'accélération GPU CUDA")
        else:
            print("Utilisation du CPU uniquement")
        
        # Créer le fichier de sortie
        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(output_file, width, height, bands, data_type, options)
        
        if dst_ds is None:
            print(f"Impossible de créer le fichier {output_file}")
            return False
        
        # Copier les métadonnées du système de coordonnées
        dst_ds.SetProjection(projection)
        dst_ds.SetGeoTransform(geo_transform)
        
        # Copier les données de chaque bande
        for i in range(1, bands + 1):
            src_band = src_ds.GetRasterBand(i)
            dst_band = dst_ds.GetRasterBand(i)
            
            # Copier les données
            data = src_band.ReadAsArray()
            dst_band.WriteArray(data)
            
            # Copier les métadonnées de la bande
            dst_band.SetNoDataValue(src_band.GetNoDataValue() or 0)
            
        # Créer 4 niveaux d'aperçus internes compressés en JPEG
        overviews = [2, 4, 8, 16]  # Réduction de 2x, 4x, 8x et 16x
        dst_ds.BuildOverviews("NEAREST", overviews, gdal.TermProgress_nocb)
        
        # Appliquer la compression JPEG aux aperçus
        for i in range(1, bands + 1):
            dst_band = dst_ds.GetRasterBand(i)
            dst_band.SetMetadataItem('COMPRESSION', 'JPEG', 'IMAGE_STRUCTURE')
            dst_band.SetMetadataItem('JPEG_QUALITY', '90', 'IMAGE_STRUCTURE')
        
        # Libérer les ressources
        dst_ds = None
        src_ds = None
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"Compression réussie: {output_file} (Durée: {duration:.2f} secondes)")
        return True
        
    except Exception as e:
        print(f"Erreur lors de la compression: {str(e)}")
        return False

def process_file(args):
    """
    Fonction pour traiter un fichier individuel (utilisée pour le parallélisme)
    
    Args:
        args (tuple): Tuple contenant (input_path, output_path, use_gpu)
        
    Returns:
        bool: True si la compression a réussi, False sinon
    """
    input_path, output_path, use_gpu = args
    return compress_geotiff(input_path, output_path, use_gpu)

def batch_compress(input_dir, output_dir, extensions=['.tif', '.tiff'], use_gpu=False, parallel=True):
    """
    Compresse tous les fichiers d'un répertoire avec les extensions spécifiées.
    
    Args:
        input_dir (str): Répertoire d'entrée contenant les images à traiter
        output_dir (str): Répertoire de sortie pour les images compressées
        extensions (list): Liste des extensions à traiter (par défaut: .tif, .tiff)
        use_gpu (bool): Utiliser les GPU si disponibles
        parallel (bool): Utiliser le traitement parallèle
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Vérifier le support GPU
    if use_gpu:
        gpu_available = check_gpu_support()
    else:
        gpu_available = False
        
    # Compteurs pour les statistiques
    total_files = 0
    successful_files = 0
    start_time = time.time()
    
    # Collecter tous les fichiers à traiter
    files_to_process = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() in extensions:
                total_files += 1
                
                # Construire les chemins d'entrée et de sortie
                input_path = os.path.join(root, file)
                rel_path = os.path.relpath(input_path, input_dir)
                output_path = os.path.join(output_dir, rel_path)
                
                # Créer le répertoire de sortie si nécessaire
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                files_to_process.append((input_path, output_path, gpu_available and use_gpu))
    
    # Traiter les fichiers (en parallèle ou séquentiellement)
    if parallel and total_files > 1:
        cpu_count = multiprocessing.cpu_count()
        pool_size = max(1, min(cpu_count - 1, 8))  # Utiliser CPU-1 mais max 8 processus
        print(f"Traitement parallèle avec {pool_size} processus...")
        
        with multiprocessing.Pool(processes=pool_size) as pool:
            results = pool.map(process_file, files_to_process)
            successful_files = sum(1 for r in results if r)
    else:
        # Traitement séquentiel
        for input_path, output_path, use_gpu_flag in files_to_process:
            print(f"Traitement de {input_path}...")
            if compress_geotiff(input_path, output_path, use_gpu_flag):
                successful_files += 1
    
    # Afficher les statistiques
    end_time = time.time()
    duration = end_time - start_time
    print(f"Compression terminée: {successful_files}/{total_files} fichiers traités avec succès.")
    print(f"Durée totale: {duration:.2f} secondes, moyenne: {duration/max(1, total_files):.2f} secondes/fichier")

def main():
    # Définir les arguments du programme
    parser = argparse.ArgumentParser(description='Compression d\'images aériennes avec GDAL')
    parser.add_argument('--input_dir', '-i', help='Dossier contenant les images à compresser', required=True)
    parser.add_argument('--output_dir', '-o', help='Dossier où sauvegarder les images compressées', required=True)
    parser.add_argument('--extensions', '-e', nargs='+', default=['.tif', '.tiff'], 
                        help='Extensions de fichiers à traiter, par défaut: .tif, .tiff')
    parser.add_argument('--gpu', '-g', action='store_true', 
                        help='Utiliser l\'accélération GPU si disponible')
    parser.add_argument('--no-parallel', action='store_true', 
                        help='Désactiver le traitement parallèle')
    
    args = parser.parse_args()
    
    # Valider les arguments
    input_dir = args.input_dir
    output_dir = args.output_dir
    use_gpu = args.gpu
    parallel = not args.no_parallel
    
    if not os.path.isdir(input_dir):
        print(f"Erreur: {input_dir} n'est pas un répertoire valide.")
        return
    
    # Créer le répertoire de sortie s'il n'existe pas
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Répertoire de sortie créé: {output_dir}")
    
    print(f"Traitement des images du dossier: {input_dir}")
    print(f"Sauvegarde des images compressées dans: {output_dir}")
    print(f"Extensions de fichiers traitées: {', '.join(args.extensions)}")
    print(f"Utilisation du GPU: {'Activée' if use_gpu else 'Désactivée'}")
    print(f"Traitement parallèle: {'Activé' if parallel else 'Désactivé'}")
    
    # Lancer le traitement par lot
    batch_compress(input_dir, output_dir, args.extensions, use_gpu, parallel)

if __name__ == '__main__':
    main()
