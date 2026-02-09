"""
Enhanced utility functions and data structures for tick-based backtesting.
Extends the original _util.py to support generic column access.
"""

from __future__ import annotations

import os
import sys
import warnings
from contextlib import contextmanager
from functools import partial
from itertools import chain
from multiprocessing import resource_tracker as _mprt
from multiprocessing import shared_memory as _mpshm
from numbers import Number
from threading import Lock
from typing import Dict, List, Optional, Sequence, Union, cast

import numpy as np
import pandas as pd

try:
    from tqdm.auto import tqdm as _tqdm
    _tqdm = partial(_tqdm, leave=False)
except ImportError:
    def _tqdm(seq, **_):
        return seq


def try_(lazy_func, default=None, exception=Exception):
    try:
        return lazy_func()
    except exception:
        return default


@contextmanager
def patch(obj, attr, newvalue):
    had_attr = hasattr(obj, attr)
    orig_value = getattr(obj, attr, None)
    setattr(obj, attr, newvalue)
    try:
        yield
    finally:
        if had_attr:
            setattr(obj, attr, orig_value)
        else:
            delattr(obj, attr)


def _as_str(value) -> str:
    if isinstance(value, (Number, str)):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return 'df'
    name = str(getattr(value, 'name', '') or '')
    if name in ('Open', 'High', 'Low', 'Close', 'Volume'):
        return name[:1]
    if callable(value):
        name = getattr(value, '__name__', value.__class__.__name__).replace('<lambda>', 'λ')
    if len(name) > 10:
        name = name[:9] + '…'
    return name


def _as_list(value) -> List:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return list(value)
    return [value]


def _batch(seq):
    # XXX: Replace with itertools.batched
    n = np.clip(int(len(seq) // (os.cpu_count() or 1)), 1, 300)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _data_period(index) -> Union[pd.Timedelta, Number]:
    """Return data index period as pd.Timedelta"""
    values = pd.Series(index[-100:])
    return values.diff().dropna().median()


def _strategy_indicators(strategy):
    return {attr: indicator
            for attr, indicator in strategy.__dict__.items()
            if isinstance(indicator, _Indicator)}.items()


def _indicator_warmup_nbars(strategy):
    if strategy is None:
        return 0
    nbars = max((np.isnan(indicator.astype(float)).argmin(axis=-1).max()
                 for _, indicator in _strategy_indicators(strategy)
                 if not indicator._opts['scatter']), default=0)
    return nbars


class _Array(np.ndarray):
    """
    ndarray extended to supply .name and other arbitrary properties
    in ._opts dict.
    """
    
    def __new__(cls, array, *, name=None, **opts):
        obj = np.asarray(array).view(cls)
        obj._name = name or ''
        obj._opts = opts.copy()
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self._name = getattr(obj, '_name', '')
        self._opts = getattr(obj, '_opts', {}).copy()

    def __reduce__(self):
        return (self.__class__,
                (np.asarray(self), ),
                {'_name': self._name, '_opts': self._opts})

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)

    @property
    def name(self):
        return self._name

    @property
    def s(self) -> pd.Series:
        """Access this array as a pandas Series"""
        return pd.Series(self, index=self._opts.get('index'), name=self.name, dtype=object)

    def __repr__(self):
        return f'<{self.__class__.__name__}(name={self.name!r}, shape={self.shape})>'


class _Indicator(_Array):
    pass


class _EnhancedData:
    """
    Enhanced data array accessor that supports both OHLCV columns
    and generic column access for tick-based data.
    
    Provides access to any DataFrame columns as numpy arrays for performance,
    while maintaining compatibility with the original _Data interface.
    """
    def __init__(self, df: pd.DataFrame):
        self.__df = df
        self.__len = len(df)  # Current length
        self.__pip: Optional[float] = None
        self.__cache: Dict[str, _Array] = {}
        self.__arrays: Dict[str, _Array] = {}
        self._update()

    def __getitem__(self, item):
        return self.__get_array(item)

    def __getattr__(self, item):
        try:
            return self.__get_array(item)
        except KeyError:
            raise AttributeError(f"Column '{item}' not in data") from None

    def _set_length(self, length):
        self.__len = length
        self.__cache.clear()

    def _update(self):
        index = self.__df.index.copy()
        self.__arrays = {col: _Array(arr, index=index)
                         for col, arr in self.__df.items()}
        # Leave index as Series because pd.Timestamp nicer API to work with
        self.__arrays['__index'] = index

    def __repr__(self):
        i = min(self.__len, len(self.__df)) - 1
        index = self.__arrays['__index'][i]
        items = ', '.join(f'{k}={v}' for k, v in self.__df.iloc[i].items())
        return f'<EnhancedData i={i} ({index}) {items}>'

    def __len__(self):
        return self.__len

    @property
    def df(self) -> pd.DataFrame:
        """Access the underlying DataFrame"""
        return (self.__df.iloc[:self.__len]
                if self.__len < len(self.__df)
                else self.__df)

    @property
    def pip(self) -> float:
        """Smallest price increment"""
        if self.__pip is None:
            # Try to calculate from Close, or fallback to a reasonable default
            close_data = self.__arrays.get('Close', self.__arrays.get('price'))
            if close_data is not None:
                self.__pip = float(10**-np.median([len(s.partition('.')[-1])
                                                   for s in close_data.astype(str)]))
            else:
                self.__pip = 0.01  # Default pip value
        return self.__pip

    def __get_array(self, key) -> _Array:
        """Get array for specified column, with caching"""
        arr = self.__cache.get(key)
        if arr is None:
            if key not in self.__arrays:
                raise KeyError(f"Column '{key}' not found in data")
            arr = self.__cache[key] = cast(_Array, self.__arrays[key][:self.__len])
        return arr

    # Standard OHLCV properties for backward compatibility
    @property
    def Open(self) -> _Array:
        return self.__get_array('Open')

    @property
    def High(self) -> _Array:
        return self.__get_array('High')

    @property
    def Low(self) -> _Array:
        return self.__get_array('Low')

    @property
    def Close(self) -> _Array:
        return self.__get_array('Close')

    @property
    def Volume(self) -> _Array:
        return self.__get_array('Volume')

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.__get_array('__index')

    # Additional convenience properties for tick data
    @property
    def price(self) -> _Array:
        """Access price column if available"""
        return self.__get_array('price')
        
    @property
    def size(self) -> _Array:
        """Access size column if available"""
        return self.__get_array('size')

    def has_column(self, column_name: str) -> bool:
        """Check if column exists in the data"""
        return column_name in self.__arrays

    def get_column(self, column_name: str, default=None) -> Optional[_Array]:
        """Get column by name, return default if not found"""
        try:
            return self.__get_array(column_name)
        except KeyError:
            return default

    def list_columns(self) -> List[str]:
        """List all available columns"""
        return [col for col in self.__arrays.keys() if col != '__index']

    # Make pickling work with our catch-all __getattr__
    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state


# Backward compatibility - use Enhanced version by default
_Data = _EnhancedData


# Shared Memory classes (unchanged from original)
if sys.version_info >= (3, 13):
    SharedMemory = _mpshm.SharedMemory
else:
    class SharedMemory(_mpshm.SharedMemory):
        # From https://github.com/python/cpython/issues/82300#issuecomment-2169035092
        __lock = Lock()

        def __init__(self, *args, track: bool = True, **kwargs):
            self._track = track
            if track:
                return super().__init__(*args, **kwargs)
            with self.__lock:
                with patch(_mprt, 'register', lambda *a, **kw: None):
                    super().__init__(*args, **kwargs)

        def unlink(self):
            if _mpshm._USE_POSIX and self._name:
                _mpshm._posixshmem.shm_unlink(self._name)
                if self._track:
                    _mprt.unregister(self._name, "shared_memory")


class SharedMemoryManager:
    """
    A simple shared memory contextmanager based on
    https://docs.python.org/3/library/multiprocessing.shared_memory.html#multiprocessing.shared_memory.SharedMemory
    """
    def __init__(self, create=False) -> None:
        self._shms: list[SharedMemory] = []
        self.__create = create

    def SharedMemory(self, *, name=None, create=False, size=0, track=True):
        shm = SharedMemory(name=name, create=create, size=size, track=track)
        shm._create = create
        # Essential to keep refs on Windows
        # https://stackoverflow.com/questions/74193377/filenotfounderror-when-passing-a-shared-memory-to-a-new-process#comment130999060_74194875  # noqa: E501
        self._shms.append(shm)
        return shm

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        for shm in self._shms:
            try:
                shm.close()
                if shm._create:
                    shm.unlink()
            except Exception:
                warnings.warn(f'Failed to unlink shared memory {shm.name!r}',
                              category=ResourceWarning, stacklevel=2)
                raise

    def arr2shm(self, vals):
        """Array to shared memory. Returns (shm_name, shape, dtype) used for restore."""
        assert vals.ndim == 1, (vals.ndim, vals.shape, vals)
        shm = self.SharedMemory(size=vals.nbytes, create=True)
        # np.array can't handle pandas' tz-aware datetimes
        # https://github.com/numpy/numpy/issues/18279
        buf = np.ndarray(vals.shape, dtype=vals.dtype.base, buffer=shm.buf)
        has_tz = getattr(vals.dtype, 'tz', None)
        buf[:] = vals.tz_localize(None) if has_tz else vals  # Copy into shared memory
        return shm.name, vals.shape, vals.dtype

    def df2shm(self, df):
        return tuple((
            (column, *self.arr2shm(values))
            for column, values in chain([(self._DF_INDEX_COL, df.index)], df.items())
        ))

    @staticmethod
    def shm2s(shm, shape, dtype) -> pd.Series:
        arr = np.ndarray(shape, dtype=dtype.base, buffer=shm.buf)
        arr.setflags(write=False)
        return pd.Series(arr, dtype=dtype)

    _DF_INDEX_COL = '__bt_index'

    @staticmethod
    def shm2df(data_shm):
        shm = [SharedMemory(name=name, create=False, track=False) for _, name, _, _ in data_shm]
        df = pd.DataFrame({
            col: SharedMemoryManager.shm2s(shm, shape, dtype)
            for shm, (col, _, shape, dtype) in zip(shm, data_shm)})
        df.set_index(SharedMemoryManager._DF_INDEX_COL, drop=True, inplace=True)
        df.index.name = None
        return df, shm