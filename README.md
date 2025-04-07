# Compress_Ortho

# Outil de Compression d'Images Aériennes avec Accélération GPU

Ce script Python permet de compresser des images aériennes volumineuses (300-500 Mo) avec les caractéristiques suivantes :
- Compression JPEG (90%)
- Espace colorimétrique YCbCr
- Format tuilé (512x512 pixels)
- 4 niveaux d'aperçus internes compressés en JPEG

Le script peut utiliser l'accélération GPU via CUDA pour un traitement beaucoup plus rapide et offre également un mode de traitement parallèle pour optimiser l'utilisation des processeurs multi-cœurs.

## Prérequis

- Python 3.6 ou supérieur
- GDAL (avec support CUDA pour l'accélération GPU)

### Installation des dépendances

```bash
# Sous Ubuntu/Debian (avec support GPU)
sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
sudo apt update
sudo apt install libgdal-dev python3-gdal

# Installation via pip
pip install gdal numpy
```

## Utilisation

### Compression d'un dossier d'images

```bash
python compress_aerial_images.py -i "/chemin/vers/dossier_source" -o "/chemin/vers/dossier_destination" --gpu
```

### Options disponibles

```
-i, --input_dir      Dossier contenant les images à compresser (obligatoire)
-o, --output_dir     Dossier où sauvegarder les images compressées (obligatoire)
-e, --extensions     Extensions de fichiers à traiter (par défaut: .tif, .tiff)
-g, --gpu            Utiliser l'accélération GPU si disponible
--no-parallel        Désactiver le traitement parallèle
```

## Exemples d'utilisation

### Compression avec GPU et traitement parallèle (recommandé)

```bash
python compress_aerial_images.py -i "/data/images_brutes" -o "/data/images_compressees" --gpu
```

### Compression de formats spécifiques

```bash
python compress_aerial_images.py -i "/data/images_brutes" -o "/data/images_compressees" -e .tif .img .raw --gpu
```

### Compression sans accélération GPU

```bash
python compress_aerial_images.py -i "/data/images_brutes" -o "/data/images_compressees"
```

### Compression sans traitement parallèle (pour machines à mémoire limitée)

```bash
python compress_aerial_images.py -i "/data/images_brutes" -o "/data/images_compressees" --no-parallel
```

## Performances

- **Avec GPU** : Pour des images de 300-500 Mo, le traitement peut être 3 à 10 fois plus rapide qu'avec CPU seul, selon le GPU.
- **Traitement parallèle** : Améliore significativement les performances sur les machines multi-cœurs.
- **Mémoire recommandée** : 
  - RAM : 8 Go minimum, 16 Go recommandé
  - GPU : 4 Go VRAM minimum, 8 Go recommandé pour des images de 300-500 Mo

## Structure du script

- Vérification du support GPU
- Traitement des arguments en ligne de commande
- Compression des images avec optimisations GPU si disponible
- Création des aperçus internes
- Mesure des performances
- Traitement parallèle des images

## Remarques

- Les images d'environ 4000 x 4000 pixels (ou plus grandes) bénéficient particulièrement de l'accélération GPU.
- Le script préserve toutes les métadonnées géospatiales des images originales.
- La compression JPEG à 90% offre un bon équilibre entre qualité et taille de fichier.
- Pour des images très volumineuses, vous pouvez augmenter la taille du cache GDAL dans le script.

## Dépannage

- Si le message "Support GPU non détecté" s'affiche, votre installation de GDAL n'a probablement pas été compilée avec le support CUDA.
- En cas d'erreur de mémoire, essayez l'option `--no-parallel` ou réduisez le nombre de processus parallèles dans le code source.
- Pour de meilleures performances GPU, assurez-vous que les derniers pilotes NVIDIA sont installés.
