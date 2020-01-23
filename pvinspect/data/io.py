'''Read and write images'''

from .image import *
from pathlib import Path
import numpy as np
from typing import Union, Tuple
from skimage import io
from .exceptions import UnsupportedModalityException
from functools import reduce
from tqdm.auto import tqdm
import logging


PathOrStr = Union[Path, str]

def __assurePath(p: PathOrStr) -> Path:
    if isinstance(p, str):
        return Path(p)
    else:
        return p

def _read_module_image(path: PathOrStr, modality: int, is_partial_module: bool, cols: int = None, rows: int = None) -> ModuleImage:
    '''Read a single image of a solar module and return it

    Args:
        path (PathOrStr): Path to the file to be read
        modality (int): The imaging modality
        cols (int): Number of columns of cells
        rows (int): Number of rows of cells

    Returns:
        image: The module image
    '''

    path = __assurePath(path)
    img = io.imread(path, as_gray=True)
    if img.dtype == '>u2':
        # big endian -> little endian
        img = img.astype(np.uint16)

    if is_partial_module:
        return PartialModuleImage(img, modality, path, cols, rows)
    else:
        return ModuleImage(img, modality, path, cols, rows)

def _read_module_images(path: PathOrStr, modality: int, same_camera: bool, is_partial_module: bool, cols: int = None, rows: int = None, N: int = 0, pattern: Union[str, Tuple[str]] = ('*.png', '*.tif', '*.tiff', '*.bmp'), allow_different_dtypes = False) -> ModuleImageSequence:
    '''Read a sequence of module images and return it

    Args:
        path (PathOrStr): Path to the sequence
        modality (int): The imaging modality
        same_camera (bool): Indicate, if all images are from the same camera and hence share the same intrinsic parameters
        cols (int): Number of columns of cells
        rows (int): Number of rows of cells
        N (int): Only read first N images
        pattern (Union[str, Tuple[str]]): Files must match any of the given pattern
        allow_different_dtypes (bool): Allow images to have different datatypes?

    Returns:
        image: The module image sequence
    '''

    path = __assurePath(path)

    if isinstance(pattern, str):
        pattern = [pattern]

    # find files and skip if more than N
    imgpaths = list(reduce(lambda x, y: x+y, [list(path.glob(pat)) for pat in pattern]))
    imgpaths.sort()
    if N > 0 and N < len(imgpaths):
        imgpaths = imgpaths[:N]

    imgs = list()
    for fn in tqdm(imgpaths):
        imgs.append(_read_module_image(fn, modality, is_partial_module, cols, rows))

    if not same_camera:
        homogeneous_types = np.all(np.array([img.dtype == imgs[0].dtype for img in imgs]))
        shapes = [img.shape for img in imgs]
        homogeneous_shapes = np.all(np.array([s == shapes[0] for s in shapes]))
        target_shape = np.max(shapes, axis=0)

        if not homogeneous_shapes:
            logging.warning('The original images are of different shape. They might not be suited for all applications (for example superresolution).')

        result = list()
        if not homogeneous_types or not homogeneous_shapes:
            for img in imgs:
                data = img.data
                if not homogeneous_types:
                    data = data.astype(np.float64)      # default type
                if not homogeneous_shapes:
                    tgt = np.full(target_shape, data.min(), dtype=data.dtype)
                    tgt[:data.shape[0],:data.shape[1]] = data
                    data = tgt
                result.append(ModuleImage(data, img.modality, img.path, img.cols, img.rows))
            imgs = result

    return ModuleImageSequence(imgs, copy=False, same_camera=same_camera, allow_different_dtypes=allow_different_dtypes)

def read_module_image(path: PathOrStr, modality: int, cols: int = None, rows: int = None) -> ModuleImage:
    '''Read a single image of a solar module and return it

    Args:
        path (PathOrStr): Path to the file to be read
        modality (int): The imaging modality
        cols (int): Number of columns of cells
        rows (int): Number of rows of cells

    Returns:
        image: The module image
    '''

    return _read_module_image(path, modality, False, cols, rows)

def read_module_images(path: PathOrStr, modality: int, same_camera: bool, cols: int = None, rows: int = None, N: int = 0, pattern: Union[str, Tuple[str]] = ('*.png', '*.tif', '*.tiff', '*.bmp'), allow_different_dtypes = False) -> ModuleImageSequence:
    '''Read a sequence of module images and return it

    Args:
        path (PathOrStr): Path to the sequence
        modality (int): The imaging modality
        same_camera (bool): Indicate, if all images are from the same camera and hence share the same intrinsic parameters
        cols (int): Number of columns of cells
        rows (int): Number of rows of cells
        N (int): Only read first N images
        pattern (Union[str, Tuple[str]]): Files must match any of the given pattern
        allow_different_dtypes (bool): Allow images to have different datatypes?

    Returns:
        image: The module image sequence
    '''

    return _read_module_images(path, modality, same_camera, False, cols, rows, N, pattern, allow_different_dtypes)

def read_partial_module_image(path: PathOrStr, modality: int, cols: int = None, rows: int = None) -> ModuleImage:
    '''Read a single partial view of a solar module and return it

    Args:
        path (PathOrStr): Path to the file to be read
        modality (int): The imaging modality
        cols (int): Number of completely visible columns of cells
        rows (int): Number of completely visible rows of cells

    Returns:
        image: The module image
    '''

    return _read_module_image(path, modality, True, cols, rows)

def read_partial_module_images(path: PathOrStr, modality: int, same_camera: bool, cols: int = None, rows: int = None, N: int = 0, pattern: Union[str, Tuple[str]] = ('*.png', '*.tif', '*.tiff', '*.bmp'), allow_different_dtypes = False) -> ModuleImageSequence:
    '''Read a sequence of partial views of solar modules and return it

    Args:
        path (PathOrStr): Path to the sequence
        modality (int): The imaging modality
        same_camera (bool): Indicate, if all images are from the same camera and hence share the same intrinsic parameters
        cols (int): Number of completely visible columns of cells
        rows (int): Number of completely visible rows of cells
        N (int): Only read first N images
        pattern (Union[str, Tuple[str]]): Files must match any of the given pattern
        allow_different_dtypes (bool): Allow images to have different datatypes?

    Returns:
        image: The module image sequence
    '''

    return _read_module_images(path, modality, same_camera, True, cols, rows, N, pattern, allow_different_dtypes)

def save_image(filename: PathOrStr, image: Image):
    '''Write an image to disk

    Args:
        filename (PathOrStr): Filename of the resulting image
        image (Image): The image
    '''

    io.imsave(filename, image.data, check_contrast=False)

def save_images(path: PathOrStr, sequence: ImageSequence, mkdir: bool = True):
    '''Write a sequence of images to disk

    Args:
        path (PathOrStr): Target directory
        sequence (ImageSequence): The sequence of images
        mkdir (bool): Automatically create missing directories
    '''

    path = __assurePath(path)

    if mkdir:
        path.mkdir(parents=True, exist_ok=True)

    for image in tqdm(sequence.images):
        if isinstance(image, CellImage):
            name = '{}_row{:02d}_col{:02d}{}'.format(image.path.stem, image.row, image.col, image.path.suffix)
        else:
            name = image.path.name
        save_image(path / name, image)
