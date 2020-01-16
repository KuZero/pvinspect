'''Provides access to demo datasets'''

from .image import ModuleImageSequence, ModuleImage, EL_IMAGE
from .io import read_module_image, read_module_images
from pathlib import Path
from google_drive_downloader import GoogleDriveDownloader as gdd
from typing import Tuple
import os

_ds_keys = {
    '20191219_poly10x6': '1B5fQPLvStuMvuYJ5CxbzyxfwuWQdfNVE'
}

def _get_dataset_key(name: str):
    if name in _ds_keys.keys():
        return _ds_keys[name]
    else:
        keys = os.getenv('PVINSPECT_KEYS').split(';')
        keys = {x.split(',')[0]: x.split(',')[1] for x in keys}
        print(keys)
        if name in keys.keys():
            return keys[name]
        else:
            raise RuntimeError('The specified dataset "{}" could not be found. Maybe you tried \
                to access a protected dataset and didn\'t set PVINSPECT_KEY_FILE environment variable?')

def _check_and_download_ds(name: str):
    ds_path = Path(__file__).parent.absolute() / 'datasets' / name
    if not ds_path.is_dir():
        k = _get_dataset_key(name)
        ds_path.mkdir(parents=True, exist_ok=False)
        gdd.download_file_from_google_drive(k, str(ds_path / 'data.zip'), unzip=True)
    return ds_path

def poly10x6(N: int = 0) -> ModuleImageSequence:
    '''Read sequence of 10x6 poly modules
    
    Args:
        N (int): Only read first N images
    '''
    p = _check_and_download_ds('20191219_poly10x6')
    return read_module_images(p, EL_IMAGE, True, 10, 6, N = N)

def caip_dataB() -> Tuple[ModuleImageSequence, ModuleImageSequence]:
    '''Read DataB from CAIP paper (private dataset)
    
    Note:
        This dataset is from the following publication:
        Hoffmann, Mathis, et al. "Fast and robust detection of solar modules in electroluminescence images."
        International Conference on Computer Analysis of Images and Patterns. Springer, Cham, 2019.

    Returns:
        images1: All modules with shape 10x6
        images2: All modules with shape 9x4
    '''
    p = _check_and_download_ds('20200114_caip')
    images1 = read_module_images(p / 'deitsch_testset' / '10x6', EL_IMAGE, False, 10, 6, allow_different_dtypes=True)
    images2 = read_module_images(p / 'deitsch_testset' / '9x4', EL_IMAGE, False, 9, 4, allow_different_dtypes=True)
    return images1, images2

def caip_dataC() -> ModuleImageSequence:
    '''Read DataC from CAIP paper (private dataset)
    
    Note:
        This dataset is from the following publication:
        Hoffmann, Mathis, et al. "Fast and robust detection of solar modules in electroluminescence images."
        International Conference on Computer Analysis of Images and Patterns. Springer, Cham, 2019.

    Returns:
        images: All modules images
    '''
    p = _check_and_download_ds('20200114_caip')
    return read_module_images(p / 'multiple', EL_IMAGE, True, 10, 6)

def caip_dataD() -> ModuleImageSequence:
    '''Read DataC from CAIP paper (private dataset)
    
    Note:
        This dataset is from the following publication:
        Hoffmann, Mathis, et al. "Fast and robust detection of solar modules in electroluminescence images."
        International Conference on Computer Analysis of Images and Patterns. Springer, Cham, 2019.

    Returns:
        images: All modules images
    '''
    p = _check_and_download_ds('20200114_caip')
    return read_module_images(p / 'rotated', EL_IMAGE, True, 10, 6)
