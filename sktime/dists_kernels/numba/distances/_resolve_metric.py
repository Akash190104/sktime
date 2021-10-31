# -*- coding: utf-8 -*-
import inspect
from typing import Callable, List, Union

import numpy as np

from sktime.dists_kernels.numba.distances._numba_utils import (
    is_no_python_compiled_callable,
)
from sktime.dists_kernels.numba.distances.base import (
    DistanceCallable,
    MetricInfo,
    NumbaDistance,
)


def _resolve_metric(
    metric: Union[str, Callable, NumbaDistance],
    x: np.ndarray,
    y: np.ndarray,
    known_metric_dict: List[MetricInfo],
    **kwargs: dict,
) -> DistanceCallable:
    """Resolve a metric from a string or callable or NumbaDistance instance.

    Parameters
    ----------
    metric: str or Callable or NumbaDistance
        The distance metric to use.
    x: np.ndarray (3d array)
        First timeseries.
    y: np.ndarray (3d array)
        Second timeseries.
    known_metric_dict: List[MetricInfo]
        List of known distance functions.
    kwargs: dict, optional
        Extra arguments for metric. Refer to each metric documentation for a list of
        possible arguments.

    Returns
    -------
    Callable[[np.ndarray, np.ndarray], float]]
        No_python compiled distance resolved from the metric input.

    Raises
    ------
    ValueError
        If a metric string provided, and is not a defined valid string.
        If a metric object (instance of class) is provided and doesn't inherit from
        NumbaDistance.
        If a resolved metric is not no_python compiled.
        If the metric type cannot be determined.
    """
    numba_dist_instance: Union[NumbaDistance, None] = None

    if isinstance(metric, NumbaDistance):
        numba_dist_instance = metric
    elif isinstance(metric, str):
        numba_dist_instance = _resolve_str_metric(metric, known_metric_dict)
    elif callable(metric):
        if _is_distance_factory_callable(metric):
            metric = metric(x[0], y[0], **kwargs)
        elif _is_no_python_distance_callable(metric):
            metric = metric
        else:
            found = False
            for val in known_metric_dict:
                if val.dist_func is metric:
                    numba_dist_instance = val.dist_instance
                    found = True
                    break
            if found is False:
                raise ValueError(
                    "The callable provided must be no_python (using njit()) for"
                    "this operation. Please compile the function and try again."
                )
    else:
        raise ValueError(
            "Unable to resolve the metric with the parameters provided."
            "The metric must be a valid string, NumbaDistance or a"
            "distance factory callable or no_python distance."
        )

    if numba_dist_instance is not None:
        metric = numba_dist_instance.distance_factory(x[0], y[0], **kwargs)

    return metric


def _resolve_str_metric(
    metric: str, known_metric_dict: List[MetricInfo]
) -> NumbaDistance:
    """Resolve a string to a NumbaDistance.

    Parameters
    ----------
    metric: str
        String to resolve to NumbaDistance.
    known_metric_dict: List[MetricInfo]
        List of known distance functions.

    Returns
    -------
    NumbaDistance
        Instance of distance resolved from string

    Raises
    ------
    ValueError
        If the metric string provided is not a known distance.
    """
    for val in known_metric_dict:
        if metric in val.aka:
            return val.dist_instance

    raise ValueError(
        f"The metric provided: {metric}, is invalid. The current list"
        f"of supported distances is {known_metric_dict}"
    )


def _is_distance_factory_callable(metric: Callable) -> bool:
    """Validate if a callable is a distance factory.

    Parameters
    ----------
    metric: Callable
        Callable to validate if is a valid distance factory.

    Returns
    -------
    bool
        Boolean that is true if callable is a valid distance factory and false
        if the callable is an invalid distance factory.
    """
    is_no_python_compiled = is_no_python_compiled_callable(metric)
    if is_no_python_compiled:
        return False
    correct_num_params = len(inspect.signature(metric).parameters) >= 2
    return_type = inspect.signature(metric).return_annotation
    return_num_params = (
        return_type is not float
        and hasattr(return_type, "__len__")
        and len(return_type) == 1
    )
    return correct_num_params and return_num_params


def _is_no_python_distance_callable(metric: Callable) -> bool:
    """Validate if a callable is a no_python compiled distance metric.

    Parameters
    ----------
    metric: Callable
        Callable to validate if is a valid no_python distance callable.

    Returns
    -------
    bool
        Boolean that is true if callable is a valid no_python compiled distance and
        false if the callable is an invalid no_python callable.

    """
    is_no_python_compiled = is_no_python_compiled_callable(metric)
    if not is_no_python_compiled:
        return False
    correct_num_params = len(inspect.signature(metric).parameters) == 2
    return_num_params = inspect.signature(metric).return_annotation is float
    return correct_num_params and return_num_params
