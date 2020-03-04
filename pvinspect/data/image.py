'''Provides classes to store and visualize images with metadata'''

import numpy as np
from skimage import io, img_as_uint, img_as_float
from pvinspect.common import Transform
from matplotlib import pyplot as plt
from pathlib import Path
from typing import List, Tuple, Union, Callable, Type, TypeVar
from copy import deepcopy
import math
from functools import wraps
import logging
from pvinspect.common._ipy_exit import exit
import inspect


# modality    
EL_IMAGE = 0
'''Indicate an electroluminescense (EL) image'''
PL_IMAGE = 1
'''Indicate a photoluminescense (PL) image'''

class _Base:

    T = TypeVar('T')

    @classmethod
    def from_other(cls: Type[T], other: T, **kwargs) -> T:
        '''Create a new image by partially overwriting the properties of another

        Args:
            other (Image): The other image
            **kwargs: Arguments that should be overwritten
        '''
        required = inspect.getfullargspec(cls.__init__)[0]

        other_args = dict()
        for name in required:
            if name not in kwargs and name != 'self':
                other_args[name] = getattr(other, '_'+name)

        return cls(**kwargs, **other_args)


class Image(_Base):
    '''A general image'''

    def __init__(self, data: np.ndarray, path: Path, modality: int = None):
        '''Create a new image. All non-float images as automatically converted to uint.

        Args:
            data (np.ndarray): The image data
            path (Path): Path to the image
            modality (int): The imaging modality (EL_IMAGE or PL_IMAGE) or None
        '''
        # convert to a common dtype
        if data.dtype != np.float32 and data.dtype != np.float64:
            data = img_as_uint(data)

        self._data = data
        self._path = path
        self._modality = modality

    def show(self, clip_low: float = 0.001, clip_high: float = 99.999):
        '''Show this image
        
        Args:
            clip_low (float): Intensity below this percentile is clipped
            clip_high (float): Intensity above this percentile is clipped
        '''
        clip_low = clip_low if clip_low is not None else 0.0
        clip_high = clip_high if clip_high is not None else 100.0
        p = np.percentile(self.data, [clip_low, clip_high])
        d = np.clip(self.data, p[0], p[1])
        plt.imshow(d, cmap='gray')
        plt.colorbar()
        plt.title(str(self.path.name))

    _T = TypeVar('T')
    def as_type(self: _T, dtype: np.ndarray.dtype) -> _T:
        if dtype == np.float32 or dtype == np.float64:
            return type(self).from_other(self, data = img_as_float(self._data))
        else:
            return type(self).from_other(self, data = img_as_uint(self._data))

    def __add__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data+other._data)
    
    def __sub__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data-other._data)
    
    def __mul__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data*other._data)
    
    def __truediv__(self: _T, other: _T) -> _T:
        if self.dtype not in (np.float64, np.float32) or other.dtype not in (np.float64, np.float32):
            raise RuntimeError('Images must be of type float')
        return type(self).from_other(self, data = self._data/other._data)
    
    def __floordiv__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data//other._data)
    
    def __mod__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data%other._data)
    
    def __pow__(self: _T, other: _T) -> _T:
        if self.dtype != other.dtype:
            raise RuntimeError('Images must have the same datatype')
        return type(self).from_other(self, data = self._data**other._data)

    @property
    def data(self) -> np.ndarray:
        '''The underlying image data'''
        return deepcopy(self._data)

    @property
    def path(self) -> Path:
        '''Path to the original image'''
        return deepcopy(self._path)

    @property
    def dtype(self) -> np.dtype:
        '''Datatype of the image'''
        return deepcopy(self.data.dtype)

    @property
    def shape(self) -> Tuple[int, int]:
        '''Shape of the image'''
        return deepcopy(self.data.shape)

    @property
    def modality(self) -> int:
        '''The imaging modality'''
        return self._modality

class ImageSequence(_Base):
    '''An immutable sequence of images, allowing for access to single images as well as analysis of the sequence'''

    def _show(self, imgs: List[Image], cols: int, *args, **kwargs):
        N = len(imgs)
        rows = math.ceil(N/cols)

        # adjust the figure size
        if self.shape is not None:
            aspect = self.shape[0]/self.shape[1]
        else:
            aspect = 1.0
        plt.figure(figsize=(6*cols,6*rows*aspect))

        for i, img in enumerate(imgs):
            plt.subplot(rows, cols, i+1)
            img.show(*args, **kwargs)

    def __init__(self, images: List[Image], same_camera: bool, allow_different_dtypes = False):
        '''Initialize a module image sequence
        
        Args:
            images (List[Image]): The list of images
            came_camera (bool): Indicates, if all images are from the same camera and hence share the same intrinsic parameters
            allow_different_dtypes (bool): Allow images to have different datatypes?
        '''

        self._images = images
        self._same_camera = same_camera
        self._allow_different_dtypes = allow_different_dtypes
        if len(self.images) == 0:
            logging.error('Creation of an empty sequence is not supported')
            exit()

        # check that all have the same modality, dimension, dtype and module configuration
        shape = self.images[0].shape
        dtype = self.images[0].dtype
        modality = self.images[0].modality
        for img in self.images:
            if img.dtype != dtype and not allow_different_dtypes:
                logging.error('Cannot create sequence from mixed dtypes. Consider using the "allow_different_dtypes" argument, when reading images.')
                exit()
            if img.shape != shape and same_camera:
                logging.error('Cannot create sequence from mixed shapes. Consider using the "same_camera" argument, when reading images.')
                exit()
            if img.modality != modality:
                logging.error('Cannot create a sequence from mixed modalities.')
                exit()

    def head(self, N: int = 4, cols: int = 2, *args, **kwargs):
        '''Show the first N images

        Args:
            N (int): Number of images to show
            cols (int): How many images to show in a column
        '''
        self._show(self.images[:N], cols, *args, **kwargs)

    def tail(self, N: int = 4, cols: int = 2, *args, **kwargs):
        '''Show the last N images

        Args:
            N (int): Number of images to show
            cols (int): How many images to show in a column
        '''
        self._show(self.images[-N:], cols, *args, **kwargs)

    _T = TypeVar('T')
    def apply_image_data(self: _T, fn: Callable[[np.ndarray], np.ndarray], *argv, **kwargs) -> _T:
        '''Apply the given callable on every image data.'''
        result = []
        for img in self._images:
            data = img.data
            res = fn(data, *argv, **kwargs)
            result.append(type(img).from_other(img, data=res))
        return type(self).from_other(self, images=result)

    def as_type(self: _T, dtype: np.ndarray.dtype) -> _T:
        '''Convert sequence to specified dtype'''
        result = []
        for img in self._images:
            result.append(img.as_type(dtype))
        return type(self).from_other(self, images=result)

    def __add__(self: _T, other: _T) -> _T:
        res = [x+y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    def __sub__(self: _T, other: _T) -> _T:
        res = [x-y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    def __mul__(self: _T, other: _T) -> _T:
        res = [x*y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    def __truediv__(self: _T, other: _T) -> _T:
        res = [x/y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)

    def __floordiv__(self: _T, other: _T) -> _T:
        res = [x//y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    def __mod__(self: _T, other: _T) -> _T:
        res = [x%y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    def __pow__(self: _T, other: _T) -> _T:
        res = [x**y for x, y in zip(self.images, other.images)]
        return type(self).from_other(self, images = res)
    
    @property
    def images(self) -> List[Image]:
        '''Access the list of images'''
        return deepcopy(self._images)

    @property
    def dtype(self) -> np.dtype:
        '''Access the image datatype'''
        return self.images[0].dtype if not self._allow_different_dtypes else None

    @property
    def shape(self) -> Tuple[int, int]:
        '''Access the image shape'''
        return self.images[0].shape if self._same_camera else None

    @property
    def modality(self) -> int:
        '''Access the imaging modaility'''
        return self.images[0].modality
    
    @property
    def same_camera(self) -> bool:
        '''Indicate, if the images originate from the same camera'''
        return self._same_camera

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, i: int) -> Image:
        return deepcopy(self.images[i])


class CellImage(Image):
    '''An image of a solar cell with additional meta data'''

    def __init__(self, data: np.ndarray, modality: int, path: Path, row: int, col: int):
        '''Initialize a cell image

        Args:
            data (np.ndarray): The image data
            modality (int): The imaging modality
            path (Path): Path to the image
            row (int): Row index (zero-based)
            col (int): Cell index (zero-based)
        '''

        super().__init__(data, path, modality)
        self._row = row
        self._col = col

    @property
    def row(self) -> int:
        '''0-based row index of the cell in the original module'''
        return self._row

    @property
    def col(self) -> int:
        '''0-based column index of the cell in the original module'''
        return self._col

    def show(self, *argv, **kwargs):
        '''Show this image'''
        super().show(*argv, **kwargs)
        plt.title('{}: (row: {:d}, col: {:d})'.format(self._path.name, self._row, self._col))


class CellImageSequence(ImageSequence):
    '''An immutable sequence of cell images, allowing for access to single images as well as analysis of the sequence'''

    def __init__(self, images: List[CellImage], copy = True):
        '''Initialize a module image sequence
        
        Args:
            images (List[CellImage]): The list of images
            copy (bool): Copy the images?
        '''

        super().__init__(images, False, copy)


class ModuleImage(Image):
    '''An image of a solar module with additional meta data'''

    def __init__(self, data: np.ndarray, modality: int, path: Path, cols: int = None, rows: int = None, transform: Transform = None):
        '''Initialize a module image

        Args:
            data (np.ndarray): The image data
            modality (int): The imaging modality
            path (Path): Path to the image
            cols (int): Number of cells in a column
            rows (int): Number of cells in a row
            transform (Transform): Transform from regular grid to module corners
        '''

        super().__init__(data, path, modality)
        self._cols = cols
        self._rows = rows
        self._transform = transform

    def grid(self) -> np.ndarray:
        '''Create a grid of corners according to the module geometry
        
        Returns:
            grid: (cols*rows, 2)-array of coordinates on a regular grid
        '''

        if self._cols is not None and self._rows is not None:
            x, y = np.mgrid[0:self.cols+1:1, 0:self.rows+1:1]
            grid = np.stack([x.flatten(), y.flatten()], axis=1)
            return grid
        else:
            logging.error('Module geometry is not initialized')
            exit()

    @property
    def cols(self):
        '''Number of cell-columns'''
        return self._cols

    @property
    def rows(self):
        '''Number of row-columns'''
        return self._rows

    @property
    def transform(self) -> Transform:
        '''Transformation from regular grid to image coordinates'''
        return deepcopy(self._transform)

    def show(self, show_cell_crossings: bool = True, *argv, **kwargs):
        '''Show this image and (optionally) the cell crossing points
        
        Args:
            show_cell_crossings (bool): Indicates, if the cell crossing points should be shown in addition to the image
        '''

        super().show(*argv, **kwargs)

        if show_cell_crossings and self.transform is not None:
            grid = self.grid()
            coords = self.transform.__call__(grid)
            plt.scatter(coords[:,0], coords[:,1], c='yellow', marker='+')


class PartialModuleImage(ModuleImage):
    '''An image of a solar module with additional meta data'''

    def __init__(self, data: np.ndarray, modality: int, path: Path, cols: int = None, rows: int = None, first_col: int = None, first_row: int = None, transform: Transform = None):
        '''Initialize a module image

        Args:
            data (np.ndarray): The image data
            modality (int): The imaging modality
            path (Path): Path to the image
            cols (int): Number of completely visible cells in a column
            rows (int): Number of completely visible cells in a row
            first_col (int): Index of the first complete column shown
            first_row (int): Index of the first complete row shown
            transform (Transform): Transform from regular grid to module corners
        '''

        super().__init__(data, modality, path, cols, rows, transform)

        self._first_col = first_col
        self._first_row = first_row


ModuleOrPartialModuleImage = Union[ModuleImage, PartialModuleImage]


class ModuleImageSequence(ImageSequence):
    '''An immutable sequence of module images, allowing for access to single images as well as analysis of the sequence'''

    def __init__(self, images: List[ModuleOrPartialModuleImage], same_camera: bool, allow_different_dtypes = False):
        '''Initialize a module image sequence
        
        Args:
            images (List[ModuleImage]): The list of images
            same_camera (bool): Indicates if all images are from the same camera
            allow_different_dtypes (bool): Allow images to have different datatypes?
        '''

        cols = images[0].cols
        rows = images[0].rows
        for img in images:
            if img.cols != cols:
                logging.error('Cannot create sequence from different module configurations')
                exit()
            if img.rows != rows:
                logging.error('Cannot create sequence from different module configurations')
                exit()

        super().__init__(images, same_camera, allow_different_dtypes)


ModuleImageOrSequence = Union[ModuleImageSequence, ModuleImage, PartialModuleImage, Image]

def _sequence(*args):
    '''Assure that the first argument is a sequence and handle the first return value accordingly'''
    def decorator_sequence(func):
        @wraps(func)
        def wrapper_sequence(*args, **kwargs):
            if not isinstance(args[0], ImageSequence):
                args = list(args)
                args[0] = ModuleImageSequence([args[0]], same_camera=False) if type(args[0]) == ModuleImage else ImageSequence([args[0]], same_camera=False)
                unwrap = True
            else:
                unwrap = False
            res = func(*tuple(args), **kwargs)
            if unwrap and not disable_unwrap:
                if isinstance(res, tuple) and isinstance(res[0], ImageSequence):
                    res[0] = res[0].images[0]
                elif isinstance(res, ImageSequence):
                    res = res.images[0]
            return res
        return wrapper_sequence

    if len(args) == 1 and callable(args[0]):
        disable_unwrap = False
        return decorator_sequence(args[0])
    else:
        disable_unwrap = args[0] if len(args) == 1 else False
        return decorator_sequence


