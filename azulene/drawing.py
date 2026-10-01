"""Raster drawing primitives with a Cartesian, canvas-centred coordinate system.

Public colours use ``(alpha, red, green, blue)`` channel order.  Pillow images
use RGBA internally, so conversion happens only at the raster boundary.
"""

from __future__ import annotations

import math as _math
import hashlib as _hashlib
from collections import OrderedDict as _OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw

ColorChannel = int | float
Color = tuple[ColorChannel, ColorChannel, ColorChannel, ColorChannel]


_DISTANCE_FIELD_CACHE: _OrderedDict[
    tuple[int, int, bytes],
    np.ndarray,
] = _OrderedDict()
_DISTANCE_FIELD_CACHE_SIZE = 8


def _squared_distance_transform_1d(values: np.ndarray) -> np.ndarray:
    """Exact squared Euclidean distance transform for one finite row."""

    length = values.size
    locations = np.empty(length, dtype=np.int32)
    intersections = np.empty(length + 1, dtype=float)
    result = np.empty(length, dtype=float)
    level = 0
    locations[0] = 0
    intersections[0] = -np.inf
    intersections[1] = np.inf
    for position in range(1, length):
        previous = locations[level]
        crossing = (
            (values[position] + position * position)
            - (values[previous] + previous * previous)
        ) / (2.0 * (position - previous))
        while crossing <= intersections[level]:
            level -= 1
            previous = locations[level]
            crossing = (
                (values[position] + position * position)
                - (values[previous] + previous * previous)
            ) / (2.0 * (position - previous))
        level += 1
        locations[level] = position
        intersections[level] = crossing
        intersections[level + 1] = np.inf

    level = 0
    for position in range(length):
        while intersections[level + 1] < position:
            level += 1
        nearest = locations[level]
        result[position] = (
            (position - nearest) * (position - nearest) + values[nearest]
        )
    return result


def _inside_distance_field(mask: np.ndarray) -> np.ndarray:
    """Return pixel-centre distance from each inside pixel to the outline."""

    height, width = mask.shape
    digest = _hashlib.blake2b(
        np.ascontiguousarray(mask, dtype=np.uint8),
        digest_size=16,
    ).digest()
    cache_key = (height, width, digest)
    cached = _DISTANCE_FIELD_CACHE.get(cache_key)
    if cached is not None:
        _DISTANCE_FIELD_CACHE.move_to_end(cache_key)
        return cached

    padded = np.pad(mask, 1, constant_values=False)
    padded_height, padded_width = padded.shape
    unreachable = float((padded_height + padded_width) ** 2)
    source = np.where(padded, unreachable, 0.0)
    horizontal = np.empty_like(source, dtype=float)
    for row in range(padded_height):
        horizontal[row] = _squared_distance_transform_1d(source[row])
    squared = np.empty_like(horizontal, dtype=float)
    for column in range(padded_width):
        squared[:, column] = _squared_distance_transform_1d(
            horizontal[:, column]
        )
    distance = np.maximum(np.sqrt(squared[1:-1, 1:-1]) - 0.5, 0.0)
    distance.setflags(write=False)
    _DISTANCE_FIELD_CACHE[cache_key] = distance
    if len(_DISTANCE_FIELD_CACHE) > _DISTANCE_FIELD_CACHE_SIZE:
        _DISTANCE_FIELD_CACHE.popitem(last=False)
    return distance


def _color(value: Sequence[ColorChannel]) -> Color:
    if len(value) not in (3, 4):
        raise ValueError("color must be an RGB or ARGB sequence")
    channels_list: list[ColorChannel] = []
    for channel in value:
        numeric = float(channel)
        if not np.isfinite(numeric):
            raise ValueError("color channels must be finite numbers")
        channels_list.append(channel)
    channels = tuple(channels_list)
    if len(channels) == 3:
        channels = (255,) + channels
    return channels  # type: ignore[return-value]


def _rgba(value: Color) -> tuple[ColorChannel, ColorChannel, ColorChannel, ColorChannel]:
    """Convert a public ARGB colour to Pillow/NumPy RGBA order."""

    alpha, red, green, blue = value
    return red, green, blue, alpha


def _xy(value: Sequence[float]) -> tuple[float, float]:
    if len(value) != 2:
        raise ValueError("a position must contain exactly two coordinates")
    return float(value[0]), float(value[1])


def _scale_factor(value: float) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric <= 0.0:
        raise ValueError("scale factors must be positive finite numbers")
    return numeric


def _angle(value: float) -> float:
    numeric = float(value)
    if not np.isfinite(numeric):
        raise ValueError("rotation must be a finite angle in degrees")
    return numeric


def _edge_refinement(value: float) -> float:
    if isinstance(value, bool):
        raise TypeError("edge refinement must be a number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError("edge refinement must be a number") from error
    if not np.isfinite(numeric):
        raise ValueError("edge refinement must be finite")
    return numeric


@dataclass(eq=False)
class Point:
    x: float
    y: float
    _color: Color = field(default=(255, 0, 0, 0), repr=False)

    @property
    def color(self) -> Color:
        return self._color

    @color.setter
    def color(self, value: Sequence[ColorChannel]) -> None:
        self._color = _color(value)


def point(
    x: float | Sequence[float],
    y: float | None = None,
) -> Point:
    """Create a coloured vertex from ``x, y`` or a two-item tuple/list."""

    if y is None:
        if isinstance(x, (str, bytes)) or not isinstance(x, Sequence):
            raise TypeError("point expects x, y or a two-item tuple/list")
        point_x, point_y = _xy(x)
    else:
        if isinstance(x, Sequence):
            raise TypeError("when y is provided, x must be a number")
        point_x, point_y = float(x), float(y)
    return Point(point_x, point_y)


class Polygon:
    """A polygon whose vertices share one colour.

    Two positions create an open, geometrically zero-width line segment.
    Three or more positions create the usual closed, filled polygon.
    """

    def __init__(self, positions: Iterable[Sequence[float]]) -> None:
        self.positions = [_xy(position) for position in positions]
        if len(self.positions) < 2:
            raise ValueError("a Polygon needs at least two positions")
        self._color: Color = (255, 0, 0, 0)
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._rot = 0.0
        # ``cut`` stores the resulting image here while retaining the geometry.
        self.image: Image.Image | None = None
        self._image_scale_x = 1.0
        self._image_scale_y = 1.0

    @property
    def color(self) -> Color:
        return self._color

    @color.setter
    def color(self, value: Sequence[ColorChannel]) -> None:
        self._color = _color(value)

    @property
    def scale_x(self) -> float:
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value: float) -> None:
        self._scale_x = _scale_factor(value)

    @property
    def scale_y(self) -> float:
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value: float) -> None:
        self._scale_y = _scale_factor(value)

    @property
    def rot(self) -> float:
        return self._rot

    @rot.setter
    def rot(self, value: float) -> None:
        self._rot = _angle(value)

    @property
    def points(self) -> list[tuple[float, float]]:
        """Alias for positions, useful when consuming a cut result."""

        return list(self.positions)

    @staticmethod
    def _signed_area(points: Sequence[tuple[float, float]]) -> float:
        return 0.5 * sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )

    @staticmethod
    def _cross(
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return first[0] * second[1] - first[1] * second[0]

    @classmethod
    def _segments_intersect(
        cls,
        first_start: tuple[float, float],
        first_end: tuple[float, float],
        second_start: tuple[float, float],
        second_end: tuple[float, float],
        epsilon: float,
    ) -> bool:
        def direction(
            start: tuple[float, float],
            end: tuple[float, float],
            point: tuple[float, float],
        ) -> float:
            return cls._cross(
                (end[0] - start[0], end[1] - start[1]),
                (point[0] - start[0], point[1] - start[1]),
            )

        def on_segment(
            start: tuple[float, float],
            end: tuple[float, float],
            point: tuple[float, float],
        ) -> bool:
            return (
                min(start[0], end[0]) - epsilon
                <= point[0]
                <= max(start[0], end[0]) + epsilon
                and min(start[1], end[1]) - epsilon
                <= point[1]
                <= max(start[1], end[1]) + epsilon
            )

        first_side = direction(first_start, first_end, second_start)
        second_side = direction(first_start, first_end, second_end)
        third_side = direction(second_start, second_end, first_start)
        fourth_side = direction(second_start, second_end, first_end)
        if (
            (first_side > epsilon and second_side < -epsilon)
            or (first_side < -epsilon and second_side > epsilon)
        ) and (
            (third_side > epsilon and fourth_side < -epsilon)
            or (third_side < -epsilon and fourth_side > epsilon)
        ):
            return True
        return (
            abs(first_side) <= epsilon
            and on_segment(first_start, first_end, second_start)
            or abs(second_side) <= epsilon
            and on_segment(first_start, first_end, second_end)
            or abs(third_side) <= epsilon
            and on_segment(second_start, second_end, first_start)
            or abs(fourth_side) <= epsilon
            and on_segment(second_start, second_end, first_end)
        )

    @classmethod
    def _has_self_intersection(
        cls,
        points: Sequence[tuple[float, float]],
        epsilon: float,
    ) -> bool:
        count = len(points)
        for first in range(count):
            first_next = (first + 1) % count
            for second in range(first + 1, count):
                second_next = (second + 1) % count
                if (
                    first == second
                    or first_next == second
                    or second_next == first
                ):
                    continue
                if cls._segments_intersect(
                    points[first],
                    points[first_next],
                    points[second],
                    points[second_next],
                    epsilon,
                ):
                    return True
        return False

    def refine_edge(self, amount: float) -> "Polygon":
        """Return a new polygon with its boundary offset by ``amount``.

        Positive values expand the polygon and negative values shrink it.
        The offset is measured in the polygon's unscaled local coordinates;
        colour, scale and rotation are copied to the returned object.  The
        operation requires a non-self-intersecting closed polygon with at
        least three points.  An offset that collapses or crosses the boundary
        raises :class:`ValueError`.
        """

        distance = _edge_refinement(amount)
        points = list(self.positions)
        if len(points) < 3:
            raise ValueError("refine_edge requires a closed Polygon")
        coordinate_scale = max(
            1.0,
            abs(distance),
            *(abs(coordinate) for point in points for coordinate in point),
        )
        epsilon = coordinate_scale * 1e-10
        area = self._signed_area(points)
        if abs(area) <= epsilon:
            raise ValueError("refine_edge requires a non-degenerate Polygon")
        if self._has_self_intersection(points, epsilon):
            raise ValueError("refine_edge requires a non-self-intersecting Polygon")

        directions: list[tuple[float, float]] = []
        normals: list[tuple[float, float]] = []
        orientation = 1.0 if area > 0.0 else -1.0
        for index, start in enumerate(points):
            end = points[(index + 1) % len(points)]
            edge_x = end[0] - start[0]
            edge_y = end[1] - start[1]
            length = _math.hypot(edge_x, edge_y)
            if length <= epsilon:
                raise ValueError("refine_edge does not accept zero-length edges")
            direction = (edge_x / length, edge_y / length)
            directions.append(direction)
            normals.append(
                (
                    orientation * direction[1],
                    -orientation * direction[0],
                )
            )

        refined: list[tuple[float, float]] = []
        for index, vertex in enumerate(points):
            previous = (index - 1) % len(points)
            previous_direction = directions[previous]
            next_direction = directions[index]
            previous_normal = normals[previous]
            next_normal = normals[index]
            previous_point = (
                vertex[0] + distance * previous_normal[0],
                vertex[1] + distance * previous_normal[1],
            )
            next_point = (
                vertex[0] + distance * next_normal[0],
                vertex[1] + distance * next_normal[1],
            )
            denominator = self._cross(previous_direction, next_direction)
            if abs(denominator) <= epsilon:
                if (
                    previous_direction[0] * next_direction[0]
                    + previous_direction[1] * next_direction[1]
                    < 0.0
                ):
                    raise ValueError("refine_edge cannot offset a 180-degree corner")
                refined.append(
                    (
                        vertex[0]
                        + distance
                        * (previous_normal[0] + next_normal[0])
                        / 2.0,
                        vertex[1]
                        + distance
                        * (previous_normal[1] + next_normal[1])
                        / 2.0,
                    )
                )
                continue
            between = (
                next_point[0] - previous_point[0],
                next_point[1] - previous_point[1],
            )
            along_previous = self._cross(between, next_direction) / denominator
            refined.append(
                (
                    previous_point[0]
                    + along_previous * previous_direction[0],
                    previous_point[1]
                    + along_previous * previous_direction[1],
                )
            )

        refined_area = self._signed_area(refined)
        if (
            abs(refined_area) <= epsilon
            or (refined_area > 0.0) != (area > 0.0)
            or self._has_self_intersection(refined, epsilon)
        ):
            raise ValueError("edge refinement collapses or crosses the Polygon")
        if distance < 0.0:
            for index, start in enumerate(refined):
                end = refined[(index + 1) % len(refined)]
                refined_edge = (end[0] - start[0], end[1] - start[1])
                original_edge = directions[index]
                if (
                    refined_edge[0] * original_edge[0]
                    + refined_edge[1] * original_edge[1]
                    <= epsilon
                ):
                    raise ValueError("edge refinement collapses the Polygon")

        result = Polygon(refined)
        result.color = self.color
        result.scale_x = self.scale_x
        result.scale_y = self.scale_y
        result.rot = self.rot
        return result

    def scale_uniform(self, factor: float) -> "Polygon":
        """Return a uniformly scaled copy without modifying this polygon.

        Scaling is performed around the polygon's local origin ``(0, 0)``.
        The same factor is applied to the existing ``scale_x`` and
        ``scale_y``, preserving their ratio as well as colour, rotation and
        any image-backed contents.
        """

        uniform_factor = _scale_factor(factor)
        result = Polygon(self.positions)
        result.color = self.color
        result.scale_x = self.scale_x * uniform_factor
        result.scale_y = self.scale_y * uniform_factor
        result.rot = self.rot
        result.image = None if self.image is None else self.image.copy()
        result._image_scale_x = self._image_scale_x
        result._image_scale_y = self._image_scale_y
        return result


ImplicitEquation = Callable[[float, float], float]


class Implicit(Polygon):
    """A polygonal boundary extracted from ``equation(x, y) == level``.

    ``x_range`` and ``y_range`` must fully contain the desired closed contour.
    When an equation produces several closed contours, the one with the
    largest absolute area is used as this object's boundary.
    """

    def __init__(
        self,
        equation: ImplicitEquation,
        x_range: Sequence[float],
        y_range: Sequence[float],
        samples: int | Sequence[int] = 256,
        level: float = 0.0,
    ) -> None:
        if not callable(equation):
            raise TypeError("Implicit equation must be callable")
        self.equation = equation
        self.x_range = self._range(x_range, "x_range")
        self.y_range = self._range(y_range, "y_range")
        self.samples = self._sample_counts(samples)
        self.level = float(level)
        if not np.isfinite(self.level):
            raise ValueError("Implicit level must be finite")
        positions = self._extract_boundary()
        super().__init__(positions)

    @staticmethod
    def _range(value: Sequence[float], name: str) -> tuple[float, float]:
        low, high = _xy(value)
        if not np.isfinite(low) or not np.isfinite(high) or low >= high:
            raise ValueError(f"Implicit {name} must contain two increasing finite values")
        return low, high

    @staticmethod
    def _sample_counts(samples: int | Sequence[int]) -> tuple[int, int]:
        if isinstance(samples, Sequence) and not isinstance(samples, (str, bytes)):
            if len(samples) != 2:
                raise ValueError("Implicit samples must be an integer or two integers")
            sample_x, sample_y = samples
        else:
            sample_x = sample_y = samples
        if (
            isinstance(sample_x, bool)
            or isinstance(sample_y, bool)
            or int(sample_x) != sample_x
            or int(sample_y) != sample_y
            or int(sample_x) < 8
            or int(sample_y) < 8
        ):
            raise ValueError("Implicit sample counts must be integers of at least 8")
        return int(sample_x), int(sample_y)

    def _values(self, x_values: np.ndarray, y_values: np.ndarray) -> np.ndarray:
        grid_x, grid_y = np.meshgrid(x_values, y_values)
        try:
            values = np.asarray(self.equation(grid_x, grid_y), dtype=float)
            if values.shape != grid_x.shape:
                raise ValueError
        except (TypeError, ValueError):
            values = np.empty_like(grid_x, dtype=float)
            for row in range(grid_x.shape[0]):
                for column in range(grid_x.shape[1]):
                    values[row, column] = float(
                        self.equation(
                            float(grid_x[row, column]),
                            float(grid_y[row, column]),
                        )
                    )
        if not np.all(np.isfinite(values)):
            raise ValueError("Implicit equation must return finite values in the search range")
        return values

    @staticmethod
    def _intersection(
        first: tuple[float, float, float],
        second: tuple[float, float, float],
        level: float,
    ) -> tuple[float, float]:
        first_x, first_y, first_value = first
        second_x, second_y, second_value = second
        difference = second_value - first_value
        amount = 0.5 if abs(difference) <= 1e-15 else (level - first_value) / difference
        amount = min(1.0, max(0.0, amount))
        return (
            first_x + (second_x - first_x) * amount,
            first_y + (second_y - first_y) * amount,
        )

    @staticmethod
    def _point_key(point: tuple[float, float]) -> tuple[float, float]:
        return round(point[0], 12), round(point[1], 12)

    def _extract_boundary(self) -> list[tuple[float, float]]:
        sample_x, sample_y = self.samples
        x_values = np.linspace(self.x_range[0], self.x_range[1], sample_x)
        y_values = np.linspace(self.y_range[0], self.y_range[1], sample_y)
        values = self._values(x_values, y_values)
        segments: set[
            tuple[tuple[float, float], tuple[float, float]]
        ] = set()

        ordinary_cases: dict[int, tuple[tuple[int, int], ...]] = {
            1: ((3, 0),),
            2: ((0, 1),),
            3: ((3, 1),),
            4: ((1, 2),),
            6: ((0, 2),),
            7: ((3, 2),),
            8: ((2, 3),),
            9: ((0, 2),),
            11: ((1, 2),),
            12: ((3, 1),),
            13: ((0, 1),),
            14: ((3, 0),),
        }
        for row in range(sample_y - 1):
            for column in range(sample_x - 1):
                corners = (
                    (x_values[column], y_values[row], values[row, column]),
                    (x_values[column + 1], y_values[row], values[row, column + 1]),
                    (
                        x_values[column + 1],
                        y_values[row + 1],
                        values[row + 1, column + 1],
                    ),
                    (x_values[column], y_values[row + 1], values[row + 1, column]),
                )
                case = sum(
                    (1 << index)
                    for index, corner in enumerate(corners)
                    if corner[2] <= self.level
                )
                if case in (0, 15):
                    continue
                edges = (
                    (corners[0], corners[1]),
                    (corners[1], corners[2]),
                    (corners[3], corners[2]),
                    (corners[0], corners[3]),
                )
                intersections = {
                    edge: self._point_key(
                        self._intersection(edges[edge][0], edges[edge][1], self.level)
                    )
                    for edge in range(4)
                }
                if case in (5, 10):
                    centre_value = sum(corner[2] for corner in corners) / 4.0
                    centre_inside = centre_value <= self.level
                    if case == 5:
                        pairs = (
                            ((0, 1), (2, 3))
                            if centre_inside
                            else ((3, 0), (1, 2))
                        )
                    else:
                        pairs = (
                            ((3, 0), (1, 2))
                            if centre_inside
                            else ((0, 1), (2, 3))
                        )
                else:
                    pairs = ordinary_cases[case]
                for first_edge, second_edge in pairs:
                    first = intersections[first_edge]
                    second = intersections[second_edge]
                    if first == second:
                        continue
                    segments.add(tuple(sorted((first, second))))

        if not segments:
            raise ValueError("Implicit equation produced no boundary in the search range")
        adjacency: dict[tuple[float, float], set[tuple[float, float]]] = {}
        for first, second in segments:
            adjacency.setdefault(first, set()).add(second)
            adjacency.setdefault(second, set()).add(first)

        remaining = set(segments)
        loops: list[list[tuple[float, float]]] = []
        while remaining:
            first, second = next(iter(remaining))
            remaining.remove((first, second))
            path = [first, second]
            previous, current = first, second
            while current != path[0]:
                candidates = [
                    candidate
                    for candidate in adjacency[current]
                    if candidate != previous
                    and tuple(sorted((current, candidate))) in remaining
                ]
                if not candidates:
                    break
                following = candidates[0]
                remaining.remove(tuple(sorted((current, following))))
                path.append(following)
                previous, current = current, following
            if path[-1] == path[0] and len(path) >= 4:
                loops.append(path[:-1])

        if not loops:
            raise ValueError(
                "Implicit boundary is not closed; enlarge x_range or y_range"
            )

        def area(loop: Sequence[tuple[float, float]]) -> float:
            return 0.5 * sum(
                loop[index][0] * loop[(index + 1) % len(loop)][1]
                - loop[(index + 1) % len(loop)][0] * loop[index][1]
                for index in range(len(loop))
            )

        boundary = max(loops, key=lambda loop: abs(area(loop)))
        if area(boundary) < 0.0:
            boundary.reverse()
        return boundary


class Circle:
    """A circle with an optional logical centre and shared boundary colour.

    ``Circle(r)`` remains centred at ``(0, 0)``.  ``Circle(r, x, y)`` stores
    its own centre, while :meth:`Canvas.put` applies an additional translation.
    Scaling and rotation act around the circle's centre.
    """

    def __init__(self, r: float, x: float = 0.0, y: float = 0.0) -> None:
        if isinstance(r, bool):
            raise TypeError("circle radius must be a number")
        self.r = float(r)
        if not np.isfinite(self.r) or self.r <= 0:
            raise ValueError("circle radius must be a positive finite number")
        if isinstance(x, bool) or isinstance(y, bool):
            raise TypeError("circle centre coordinates must be numbers")
        self.x = float(x)
        self.y = float(y)
        if not np.isfinite(self.x) or not np.isfinite(self.y):
            raise ValueError("circle centre coordinates must be finite")
        self._color: Color = (255, 0, 0, 0)
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._rot = 0.0
        self.image: Image.Image | None = None
        self._image_scale_x = 1.0
        self._image_scale_y = 1.0

    @property
    def radius(self) -> float:
        return self.r

    @property
    def color(self) -> Color:
        return self._color

    @color.setter
    def color(self, value: Sequence[ColorChannel]) -> None:
        self._color = _color(value)

    @property
    def scale_x(self) -> float:
        return self._scale_x

    @scale_x.setter
    def scale_x(self, value: float) -> None:
        self._scale_x = _scale_factor(value)

    @property
    def scale_y(self) -> float:
        return self._scale_y

    @scale_y.setter
    def scale_y(self, value: float) -> None:
        self._scale_y = _scale_factor(value)

    @property
    def rot(self) -> float:
        return self._rot

    @rot.setter
    def rot(self, value: float) -> None:
        self._rot = _angle(value)

    def refine_edge(self, amount: float) -> "Circle":
        """Return a new circle whose radius is offset by ``amount``.

        Positive values expand the circle and negative values shrink it.
        The centre, colour, scale and rotation are copied to the new object.
        """

        radius = self.r + _edge_refinement(amount)
        if radius <= 0.0:
            raise ValueError("edge refinement must leave a positive circle radius")
        result = Circle(radius, self.x, self.y)
        result.color = self.color
        result.scale_x = self.scale_x
        result.scale_y = self.scale_y
        result.rot = self.rot
        return result

    def scale_uniform(self, factor: float) -> "Circle":
        """Return a uniformly scaled copy centred on the same circle centre."""

        uniform_factor = _scale_factor(factor)
        result = Circle(self.r, self.x, self.y)
        result.color = self.color
        result.scale_x = self.scale_x * uniform_factor
        result.scale_y = self.scale_y * uniform_factor
        result.rot = self.rot
        result.image = None if self.image is None else self.image.copy()
        result._image_scale_x = self._image_scale_x
        result._image_scale_y = self._image_scale_y
        return result


RadialProfile = Callable[[float], float]


class RadialScale(Polygon):
    """Deform a circle by changing its radius as the angle changes.

    Angles are local degrees: 0 points along ``+x`` and positive values turn
    counter-clockwise.  ``angle_step`` controls both angular sampling and the
    discrete increment interval.  With no ``profile``, the scale at an angle
    is ``start_scale + step_index * scale_increment``.  A callable profile
    may instead return the scale directly for each angle.

    The returned object is a normal closed :class:`Polygon`, so it can be
    coloured, transformed, passed to :meth:`Canvas.fill_color`, or refined.
    """

    def __init__(
        self,
        source: Circle,
        profile: RadialProfile | None = None,
        *,
        angle_step: float = 0.5,
        start_scale: float = 1.0,
        scale_increment: float = 0.0,
        start_angle: float = 0.0,
    ) -> None:
        if not isinstance(source, Circle):
            raise TypeError("RadialScale source must be a Circle")
        if source.image is not None:
            raise ValueError("RadialScale requires a geometric Circle")
        if profile is not None and not callable(profile):
            raise TypeError("RadialScale profile must be callable")
        if isinstance(angle_step, bool):
            raise TypeError("RadialScale angle_step must be a number")
        step = float(angle_step)
        if not np.isfinite(step) or step <= 0.0 or step > 120.0:
            raise ValueError(
                "RadialScale angle_step must be finite and between 0 and 120"
            )
        sample_count = int(_math.ceil(360.0 / step))
        if sample_count > 100_000:
            raise ValueError("RadialScale angle_step creates too many samples")
        initial = float(start_scale)
        increment = float(scale_increment)
        beginning = _angle(start_angle) % 360.0
        if (
            not np.isfinite(initial)
            or not np.isfinite(increment)
            or initial <= 0.0
        ):
            raise ValueError(
                "RadialScale start_scale must be positive and increments finite"
            )

        rotation = _math.radians(source.rot)
        rotation_cosine = _math.cos(rotation)
        rotation_sine = _math.sin(rotation)
        positions: list[tuple[float, float]] = []
        for index in range(sample_count):
            angle = index * step
            if angle >= 360.0:
                break
            relative_angle = (angle - beginning) % 360.0
            if profile is None:
                step_index = int(
                    _math.floor(relative_angle / step + 1e-12)
                )
                radial_scale = initial + step_index * increment
            else:
                radial_scale = float(profile(relative_angle))
            if not np.isfinite(radial_scale) or radial_scale <= 0.0:
                raise ValueError(
                    "RadialScale profile must return positive finite scales"
                )

            radians = _math.radians(angle)
            local_x = (
                source.r
                * _math.cos(radians)
                * radial_scale
                * source.scale_x
            )
            local_y = (
                source.r
                * _math.sin(radians)
                * radial_scale
                * source.scale_y
            )
            positions.append(
                (
                    source.x
                    + local_x * rotation_cosine
                    - local_y * rotation_sine,
                    source.y
                    + local_x * rotation_sine
                    + local_y * rotation_cosine,
                )
            )

        super().__init__(positions)
        self.source = source
        self.profile = profile
        self.angle_step = step
        self.start_scale = initial
        self.scale_increment = increment
        self.start_angle = beginning
        self.color = source.color


class _SquareFlame:
    """Deterministic, colour-independent animated heat-flow field.

    Heat is emitted around a head, transported through a noisy velocity field,
    diffused, cooled and split into separate trailing tongues.  Simulation is
    cached independently of colour, allowing one instance to produce matching
    animation frames for any number of colour variants.

    The object renders only the flame.  A separate :class:`Circle` can be
    composited afterwards when a stable white core is wanted.
    """

    _substeps = 6
    _temperature_stops = np.asarray(
        [0.0, 0.12, 0.30, 0.52, 0.70, 1.0],
        dtype=float,
    )

    def __init__(
        self,
        size: int = 64,
        frames: int = 6,
        seed: int = 2009307696,
        thickness: float = 8.5,
        head_motion: float = 0.5,
        rear_fullness: float = 1.5,
        turbulence: float = 1.5,
        tail_motion: float = 1.2,
        tail_chaos: float = 1.5,
        tail_flow: float = 1.9,
        side_tail_ratio: float = 0.7,
        shadow_strength: float = 0.5,
        tail_length: float = 30.0,
        tail_width: float = 8.0,
        tail_strength: float = 0.62,
        tail_separation: float = 0.15,
        wind_strength: float = 6.0,
        front_compression: float = 0.32,
        cooling: float = 0.020,
    ) -> None:
        if isinstance(size, bool) or int(size) < 16:
            raise ValueError("Flame size must be an integer of at least 16")
        if isinstance(frames, bool) or not 4 <= int(frames) <= 8:
            raise ValueError("Flame frames must be an integer from 4 to 8")
        if isinstance(seed, bool) or int(seed) < 0:
            raise ValueError("Flame seed must be a non-negative integer")
        self.size = int(size)
        self.frames = int(frames)
        self.seed = int(seed)
        self.thickness = self._bounded(thickness, "thickness", 1.0, 20.0)
        self.head_motion = self._bounded(head_motion, "head_motion", 0.0, 3.0)
        self.rear_fullness = self._bounded(
            rear_fullness, "rear_fullness", 0.8, 1.7
        )
        self.turbulence = self._bounded(turbulence, "turbulence", 0.0, 4.0)
        self.tail_motion = self._bounded(tail_motion, "tail_motion", 0.0, 4.0)
        self.tail_chaos = self._bounded(tail_chaos, "tail_chaos", 0.0, 3.0)
        self.tail_flow = self._bounded(tail_flow, "tail_flow", 0.5, 3.0)
        self.side_tail_ratio = self._bounded(
            side_tail_ratio, "side_tail_ratio", 0.2, 1.0
        )
        self.shadow_strength = self._bounded(
            shadow_strength, "shadow_strength", 0.0, 1.0
        )
        self.tail_length = self._bounded(
            tail_length, "tail_length", np.nextafter(0.0, 1.0), None
        )
        self.tail_width = self._bounded(tail_width, "tail_width", 1.0, 24.0)
        self.tail_strength = self._bounded(
            tail_strength, "tail_strength", 0.0, 1.0
        )
        self.tail_separation = self._bounded(
            tail_separation, "tail_separation", 0.0, 1.5
        )
        self.wind_strength = self._bounded(
            wind_strength, "wind_strength", 0.0, 6.0
        )
        self.front_compression = self._bounded(
            front_compression, "front_compression", 0.0, 0.5
        )
        self.cooling = self._bounded(
            cooling,
            "cooling",
            np.nextafter(0.0, 1.0),
            np.nextafter(1.0, 0.0),
        )
        self._states: tuple[tuple[np.ndarray, np.ndarray], ...] | None = None
        self.image: Image.Image | None = None

    @staticmethod
    def _bounded(
        value: float,
        name: str,
        low: float,
        high: float | None,
    ) -> float:
        numeric = float(value)
        if not np.isfinite(numeric):
            raise ValueError(f"Flame {name} must be finite")
        if numeric < low or (high is not None and numeric > high):
            allowed = f"{low} to {high}" if high is not None else f">= {low}"
            raise ValueError(f"Flame {name} must be {allowed}")
        return numeric

    @staticmethod
    def _smoothstep(value: np.ndarray | float) -> np.ndarray:
        amount = np.clip(value, 0.0, 1.0)
        return amount * amount * (3.0 - 2.0 * amount)

    def _smooth_noise(
        self,
        rng: np.random.Generator,
        cells: int,
    ) -> np.ndarray:
        small = rng.normal(0.0, 1.0, (cells, cells)).astype(np.float32)
        large = Image.fromarray(small).resize(
            (self.size, self.size),
            Image.Resampling.BICUBIC,
        )
        result = np.asarray(large, dtype=np.float64)
        result -= result.mean()
        return np.clip(result / (result.std() + 1e-8), -2.2, 2.2) / 2.2

    def _make_noise(self) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        return np.asarray(
            [
                [
                    0.7 * self._smooth_noise(rng, 5)
                    + 0.3 * self._smooth_noise(rng, 11),
                    self._smooth_noise(rng, 7),
                    self._smooth_noise(rng, 8),
                    self._smooth_noise(rng, 14),
                ]
                for _ in range(self.frames)
            ]
        )

    def _sample(
        self,
        field: np.ndarray,
        sample_x: np.ndarray,
        sample_y: np.ndarray,
    ) -> np.ndarray:
        x0 = np.floor(sample_x).astype(int)
        y0 = np.floor(sample_y).astype(int)
        weight_x = sample_x - x0
        weight_y = sample_y - y0
        output = np.zeros_like(field)
        for offset_x, offset_y, weight in (
            (0, 0, (1.0 - weight_x) * (1.0 - weight_y)),
            (1, 0, weight_x * (1.0 - weight_y)),
            (0, 1, (1.0 - weight_x) * weight_y),
            (1, 1, weight_x * weight_y),
        ):
            columns = x0 + offset_x
            rows = y0 + offset_y
            valid = (
                (columns >= 0)
                & (columns < self.size)
                & (rows >= 0)
                & (rows < self.size)
            )
            output += (
                field[
                    np.clip(rows, 0, self.size - 1),
                    np.clip(columns, 0, self.size - 1),
                ]
                * weight
                * valid
            )
        return output

    @staticmethod
    def _blur(field: np.ndarray) -> np.ndarray:
        padded = np.pad(field, 1)
        return (
            padded[1:-1, 1:-1] * 4.0
            + padded[1:-1, :-2]
            + padded[1:-1, 2:]
            + padded[:-2, 1:-1]
            + padded[2:, 1:-1]
        ) / 8.0

    def _geometry(self) -> dict[str, np.ndarray]:
        scale = self.size / 64.0
        y, x = np.mgrid[: self.size, : self.size]
        dx = x - (32.0 * scale - 0.5)
        dy = y - (24.0 * scale - 0.5)
        radius = np.hypot(dx, dy / 1.06)
        rear = self._smoothstep(dy / (10.0 * scale))
        motion = self.head_motion * (1.0 - rear) + self.tail_motion * rear
        source_radius = np.hypot(
            dx,
            dy / (1.06 * (1.0 + (self.rear_fullness - 1.0) * rear)),
        )
        obstacle_radius = 16.0 * scale
        distance_squared = np.maximum(
            dx * dx + dy * dy,
            obstacle_radius * obstacle_radius,
        )
        obstacle = obstacle_radius * obstacle_radius / distance_squared
        wind = self.wind_strength * scale
        wind_x = -2.0 * wind * obstacle * dx * dy / distance_squared
        wind_y = wind * (
            1.0 + obstacle * (dx * dx - dy * dy) / distance_squared
        )
        front = np.clip(
            -dy / np.maximum(np.hypot(dx, dy), scale),
            0.0,
            1.0,
        )
        tip = self._smoothstep((dy - 19.0 * scale) / (16.0 * scale))
        stretch = 1.0 + 0.3 * (self.tail_flow - 1.0)
        noise_y = y - rear * dy * (1.0 - 1.0 / stretch)
        side_weight = self._smoothstep(
            np.abs(dx) / ((13.2 + self.thickness) * scale)
        )
        tail_end = (
            33.0
            + self.tail_length
            * (1.0 - (1.0 - self.side_tail_ratio) * side_weight)
        ) * scale
        end_fade = self._smoothstep(
            (tail_end + 2.0 * scale - y) / (8.0 * scale)
        )
        return {
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
            "radius": radius,
            "rear": rear,
            "motion": motion,
            "source_radius": source_radius,
            "wind_x": wind_x,
            "wind_y": wind_y,
            "front": front,
            "tip": tip,
            "noise_y": noise_y,
            "end_fade": end_fade,
        }

    def _emitter(
        self,
        geometry: dict[str, np.ndarray],
        shape: np.ndarray,
        flicker: np.ndarray,
        detail: np.ndarray,
    ) -> np.ndarray:
        scale = self.size / 64.0
        outer = (
            13.2
            + self.thickness * (1.0 - self.front_compression * geometry["front"])
        ) * scale
        outer += (
            5.0
            * scale
            * self.turbulence
            * geometry["motion"]
            * shape
        )
        body = self._smoothstep(
            (outer + 2.8 * scale - geometry["source_radius"])
            / (5.6 * scale)
        )
        body *= np.clip(0.61 + 0.24 * flicker + 0.1 * shape, 0.3, 0.88)
        body *= 1.0 - self._smoothstep(
            (geometry["dy"] - 11.0 * scale) / (12.0 * scale)
        )
        body *= 0.8 + 0.32 * self.tail_strength
        body *= np.clip(
            1.0
            - 0.7
            * self.tail_chaos
            * np.maximum(detail, 0.0)
            * geometry["tip"],
            0.15,
            1.0,
        )
        return body

    def _split_tail(
        self,
        geometry: dict[str, np.ndarray],
        heat: np.ndarray,
        shape: np.ndarray,
        flicker: np.ndarray,
        detail: np.ndarray,
    ) -> np.ndarray:
        scale = self.size / 64.0
        depth = self._smoothstep(
            (geometry["dy"] - 14.0 * scale) / (12.0 * scale)
        )
        centre_column = int(np.clip(round(31.0 * scale), 0, self.size - 1))
        bend = (
            1.8
            * scale
            * self.tail_motion
            * (
                0.65 * shape[:, centre_column : centre_column + 1]
                + 0.35 * detail[:, centre_column : centre_column + 1]
            )
            * depth
        )
        notch = np.zeros_like(heat)
        for side, source_column in ((-1.0, 23.0), (1.0, 40.0)):
            column = int(np.clip(round(source_column * scale), 0, self.size - 1))
            centre = (
                32.0 * scale
                - 0.5
                + side * self.tail_width * 0.78 * scale
                + bend
            )
            centre += (
                2.8
                * scale
                * self.tail_motion
                * shape[:, column : column + 1]
                * depth
            )
            width = (1.2 + 1.6 * depth) * scale
            groove = np.exp(-((geometry["x"] - centre) / width) ** 4)
            strength = np.clip(
                0.75 + 1.6 * flicker[:, column : column + 1],
                0.3,
                1.0,
            )
            notch = np.maximum(notch, groove * strength)
        return heat * np.clip(
            1.0 - self.tail_separation * notch * depth,
            0.0,
            1.0,
        ) ** 2

    def simulate(self) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        """Run the flow once and return ``(heat, shading)`` for every frame."""

        if self._states is not None:
            return self._states
        geometry = self._geometry()
        keys = self._make_noise()
        heat = np.zeros((self.size, self.size), dtype=float)
        output: list[tuple[np.ndarray, np.ndarray]] = []
        cycle = self.frames * self._substeps
        scale = self.size / 64.0
        for step in range(cycle * 7):
            phase = step % cycle
            key, fraction = divmod(phase, self._substeps)
            blend = self._smoothstep(fraction / self._substeps)
            mixed = (
                keys[key] * (1.0 - blend)
                + keys[(key + 1) % self.frames] * blend
            )
            shape, flow = mixed[:2]
            flicker, detail = [
                self._sample(field, geometry["x"], geometry["noise_y"])
                for field in mixed[2:]
            ]
            gradient_y, gradient_x = np.gradient(flow)
            activity = (
                self.turbulence
                * geometry["motion"]
                * (1.0 + 0.35 * self.tail_chaos * geometry["rear"])
            )
            velocity_x = geometry["wind_x"] + activity * (
                12.0 * scale * gradient_y + 0.85 * scale * detail
            ) / _math.sqrt(self.tail_flow)
            velocity_y = geometry["wind_y"] + activity * (
                -12.0 * scale * gradient_x + 0.6 * scale * flicker
            )
            velocity_y += (
                self.wind_strength
                * scale
                * (self.tail_flow - 1.0)
                * geometry["rear"]
            )
            downwind_minimum = 0.6 * self.wind_strength * self.tail_flow * scale
            velocity_y = (
                velocity_y * (1.0 - geometry["rear"])
                + np.maximum(velocity_y, downwind_minimum) * geometry["rear"]
            )
            velocity_x += (
                (0.18 + 0.3 * geometry["rear"])
                * geometry["dx"]
                / np.maximum(geometry["radius"], scale)
                * scale
            )
            velocity_y += (
                (0.14 + 0.22 * geometry["rear"])
                * geometry["dy"]
                / np.maximum(geometry["radius"], scale)
                * scale
            )
            transported = self._sample(
                heat,
                geometry["x"] - velocity_x,
                geometry["y"] - velocity_y,
            )
            diffusion = 0.18 * (1.0 - 0.65 * geometry["rear"])
            heat = (
                (1.0 - diffusion) * transported
                + diffusion * self._blur(transported)
            )
            heat -= self.cooling * (1.1 + 0.8 * detail) * (
                1.0 + 1.8 * geometry["tip"]
            )
            heat = np.maximum(
                heat,
                self._emitter(geometry, shape, flicker, detail),
            )
            erosion = (
                self.tail_chaos
                * geometry["tip"]
                * np.maximum(detail - 0.05, 0.0)
            )
            heat *= np.clip(1.0 - 0.28 * erosion, 0.25, 1.0)
            heat = self._split_tail(
                geometry,
                heat,
                shape,
                flicker,
                detail,
            )
            heat *= geometry["end_fade"]
            heat = np.clip(heat, 0.0, 1.0)
            border = max(2, round(2.0 * scale))
            heat[:border] = heat[-border:] = 0.0
            heat[:, :border] = heat[:, -border:] = 0.0
            if (
                step >= cycle * 6
                and phase % self._substeps == self._substeps - 1
            ):
                shadow_noise = 0.55 * flicker + 0.35 * shape + 0.25 * detail
                darkness = self._smoothstep((shadow_noise + 0.2) / 0.55)
                shading = 1.0 - self.shadow_strength * darkness
                output.append((heat.copy(), shading))
        self._states = tuple(output)
        return self._states

    @staticmethod
    def palette(color: Sequence[ColorChannel]) -> np.ndarray:
        """Build the six temperature colours for one ARGB target colour."""

        _alpha, red, green, blue = _color(color)
        target = np.clip(
            np.asarray((red, green, blue), dtype=float),
            0.0,
            255.0,
        )
        target_amount = np.asarray([0.11, 0.31, 0.60, 0.82, 0.90, 0.39])
        white_amount = np.asarray([0.0, 0.0, 0.012, 0.05, 0.11, 0.61])
        return np.clip(
            target_amount[:, None] * target[None, :]
            + white_amount[:, None] * 255.0,
            0.0,
            255.0,
        )

    def colorize(
        self,
        state: tuple[np.ndarray, np.ndarray],
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> Image.Image:
        """Convert one heat state to a straight-alpha RGBA frame."""

        heat, shading = state
        public_color = _color(color)
        colors = (
            self.palette(public_color)
            if palette is None
            else np.asarray(palette, dtype=float)
        )
        if colors.shape != (6, 3) or not np.all(np.isfinite(colors)):
            raise ValueError("Flame palette must contain six finite RGB colours")
        temperature = heat * shading
        rgb = np.stack(
            [
                np.interp(
                    temperature,
                    self._temperature_stops,
                    colors[:, channel],
                )
                for channel in range(3)
            ],
            axis=-1,
        )
        scale = self.size / 64.0
        y, x = np.mgrid[: self.size, : self.size]
        rear = self._smoothstep((y - 34.0 * scale) / (12.0 * scale))
        glow = self._blur(heat) * (0.35 - 0.23 * rear)
        density = np.maximum(heat, glow)
        alpha = np.clip(
            (density - (0.045 + 0.065 * rear)) / 0.43,
            0.0,
            1.0,
        ) ** (1.0 + 0.2 * rear)
        edge = np.minimum.reduce(
            [x, y, self.size - 1 - x, self.size - 1 - y]
        )
        alpha *= self._smoothstep((edge - scale) / (4.0 * scale))
        alpha *= np.clip(float(public_color[0]), 0.0, 255.0) / 255.0
        rgba = np.dstack((rgb, 255.0 * alpha))
        pixels = np.clip(rgba, 0.0, 255.0).astype(np.uint8)
        pixels[pixels[..., 3] == 0, :3] = 0
        return Image.fromarray(pixels, mode="RGBA")

    def render(
        self,
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> list[Image.Image]:
        """Render every cached simulation state in one colour."""

        return [
            self.colorize(state, color, palette=palette)
            for state in self.simulate()
        ]

    def atlas(
        self,
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> Image.Image:
        """Return the frames as one horizontal transparent sprite sheet."""

        frames = self.render(color, palette=palette)
        result = Image.new(
            "RGBA",
            (self.size * len(frames), self.size),
            (0, 0, 0, 0),
        )
        for index, frame in enumerate(frames):
            result.alpha_composite(frame, (index * self.size, 0))
        self.image = result
        return result

    def save(
        self,
        path: str | Path,
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> Path:
        """Save the frames as one horizontal transparent sprite sheet."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.atlas(color, palette=palette).save(destination)
        return destination


class Flame(_SquareFlame):
    """Animated flame field with rectangular output and automatic tail fitting.

    ``size`` accepts either one integer for a square frame or ``(width,
    height)``.  Simulation may extend beyond the requested height until every
    flame tongue has naturally dissipated.  Only the tail is then fitted into
    the requested frame; the head remains at its original size and position.
    """

    def __init__(
        self,
        size: int | Sequence[int] = 64,
        frames: int = 6,
        seed: int = 2009307696,
        variation: float = 1.0,
        thickness: float = 8.5,
        head_motion: float = 0.5,
        rear_fullness: float = 1.5,
        turbulence: float = 1.5,
        tail_motion: float = 1.2,
        tail_chaos: float = 1.5,
        tail_flow: float = 1.9,
        side_tail_ratio: float = 0.7,
        shadow_strength: float = 0.5,
        tail_length: float = 30.0,
        tail_width: float = 8.0,
        tail_strength: float = 0.62,
        tail_separation: float = 0.15,
        wind_strength: float = 6.0,
        front_compression: float = 0.32,
        cooling: float = 0.020,
        margin: int = 6,
        tail_fit_start: int = 44,
    ) -> None:
        if isinstance(size, Sequence) and not isinstance(size, (str, bytes)):
            if len(size) != 2:
                raise ValueError("Flame size must be an integer or (width, height)")
            width_value, height_value = size
        else:
            width_value = height_value = size
        if (
            isinstance(width_value, bool)
            or isinstance(height_value, bool)
            or int(width_value) != width_value
            or int(height_value) != height_value
            or int(width_value) < 16
            or int(height_value) < 16
        ):
            raise ValueError("Flame dimensions must be integers of at least 16")
        if isinstance(frames, bool) or int(frames) != frames or int(frames) < 1:
            raise ValueError("Flame frames must be a positive integer")
        if isinstance(seed, bool) or int(seed) != seed or int(seed) < 0:
            raise ValueError("Flame seed must be a non-negative integer")
        if (
            isinstance(margin, bool)
            or int(margin) != margin
            or int(margin) < 0
        ):
            raise ValueError("Flame margin must be a non-negative integer")
        if (
            isinstance(tail_fit_start, bool)
            or int(tail_fit_start) != tail_fit_start
            or int(tail_fit_start) < 0
        ):
            raise ValueError("Flame tail_fit_start must be a non-negative integer")

        self.width = int(width_value)
        self.height = int(height_value)
        # The inherited emitter uses the original 64-pixel horizontal scale.
        self.size = self.width
        self.frames = int(frames)
        self.seed = int(seed)
        self.variation = self._bounded(variation, "variation", 0.0, 1.0)
        self.thickness = self._bounded(thickness, "thickness", 1.0, 20.0)
        self.head_motion = self._bounded(head_motion, "head_motion", 0.0, 3.0)
        self.rear_fullness = self._bounded(
            rear_fullness, "rear_fullness", 0.8, 1.7
        )
        self.turbulence = self._bounded(turbulence, "turbulence", 0.0, 4.0)
        self.tail_motion = self._bounded(tail_motion, "tail_motion", 0.0, 4.0)
        self.tail_chaos = self._bounded(tail_chaos, "tail_chaos", 0.0, 3.0)
        self.tail_flow = self._bounded(tail_flow, "tail_flow", 0.5, 3.0)
        self.side_tail_ratio = self._bounded(
            side_tail_ratio, "side_tail_ratio", 0.2, 1.0
        )
        self.shadow_strength = self._bounded(
            shadow_strength, "shadow_strength", 0.0, 1.0
        )
        self.tail_length = self._bounded(
            tail_length, "tail_length", np.nextafter(0.0, 1.0), None
        )
        self.tail_width = self._bounded(tail_width, "tail_width", 1.0, 24.0)
        self.tail_strength = self._bounded(
            tail_strength, "tail_strength", 0.0, 1.0
        )
        self.tail_separation = self._bounded(
            tail_separation, "tail_separation", 0.0, 1.5
        )
        self.wind_strength = self._bounded(
            wind_strength, "wind_strength", 0.0, 6.0
        )
        self.front_compression = self._bounded(
            front_compression, "front_compression", 0.0, 0.5
        )
        self.cooling = self._bounded(
            cooling,
            "cooling",
            np.nextafter(0.0, 1.0),
            np.nextafter(1.0, 0.0),
        )
        self.margin = int(margin)
        self.tail_fit_start = int(tail_fit_start)
        if self.margin >= self.height:
            raise ValueError("Flame margin must be smaller than the frame height")
        if self.tail_fit_start >= self.height - self.margin:
            raise ValueError(
                "Flame tail_fit_start must be above the fitted tail endpoint"
            )
        self._states: tuple[tuple[np.ndarray, np.ndarray], ...] | None = None
        self._last_visible_row: int | None = None
        self.image: Image.Image | None = None

    def _smooth_noise(
        self,
        rng: np.random.Generator,
        cells: int,
    ) -> np.ndarray:
        small = rng.normal(0.0, 1.0, (cells, cells)).astype(np.float32)
        large = Image.fromarray(small).resize(
            (self.width, 64),
            Image.Resampling.BICUBIC,
        )
        result = np.asarray(large, dtype=np.float64)
        result -= result.mean()
        return np.clip(result / (result.std() + 1e-8), -2.2, 2.2) / 2.2

    def _noise_block(self, rng: np.random.Generator) -> np.ndarray:
        return np.asarray(
            [
                [
                    0.7 * self._smooth_noise(rng, 5)
                    + 0.3 * self._smooth_noise(rng, 11),
                    self._smooth_noise(rng, 7),
                    self._smooth_noise(rng, 8),
                    self._smooth_noise(rng, 14),
                ]
                for _ in range(self.frames)
            ]
        )

    def _make_noise(self, height: int) -> np.ndarray:
        keys = self._noise_block(np.random.default_rng(self.seed))
        extra_rng = np.random.default_rng(self.seed ^ 0x9E3779B9)
        while keys.shape[2] < height:
            block = self._noise_block(extra_rng)
            blend = self._smoothstep(np.arange(1, 9) / 8.0)[
                None, None, :, None
            ]
            block[:, :, :8] = (
                keys[:, :, -1:, :] * (1.0 - blend)
                + block[:, :, :8] * blend
            )
            keys = np.concatenate((keys, block), axis=2)
        keys = keys[:, :, :height]
        if self.variation == 1.0:
            return keys
        reference = keys.mean(axis=0, keepdims=True)
        return reference + self.variation * (keys - reference)

    def _sample(
        self,
        field: np.ndarray,
        sample_x: np.ndarray,
        sample_y: np.ndarray,
    ) -> np.ndarray:
        height, width = field.shape
        x0 = np.floor(sample_x).astype(int)
        y0 = np.floor(sample_y).astype(int)
        weight_x = sample_x - x0
        weight_y = sample_y - y0
        output = np.zeros_like(field)
        for offset_x, offset_y, weight in (
            (0, 0, (1.0 - weight_x) * (1.0 - weight_y)),
            (1, 0, weight_x * (1.0 - weight_y)),
            (0, 1, (1.0 - weight_x) * weight_y),
            (1, 1, weight_x * weight_y),
        ):
            columns = x0 + offset_x
            rows = y0 + offset_y
            valid = (
                (columns >= 0)
                & (columns < width)
                & (rows >= 0)
                & (rows < height)
            )
            output += (
                field[
                    np.clip(rows, 0, height - 1),
                    np.clip(columns, 0, width - 1),
                ]
                * weight
                * valid
            )
        return output

    def _geometry(self, height: int) -> dict[str, np.ndarray]:
        y, x = np.mgrid[:height, : self.width]
        dx = x - (self.width - 1) / 2.0
        dy = y - 23.5
        radius = np.hypot(dx, dy / 1.06)
        rear = self._smoothstep(dy / 10.0)
        motion = self.head_motion * (1.0 - rear) + self.tail_motion * rear
        source_radius = np.hypot(
            dx,
            dy / (1.06 * (1.0 + (self.rear_fullness - 1.0) * rear)),
        )
        distance_squared = np.maximum(dx * dx + dy * dy, 16.0**2)
        obstacle = 16.0**2 / distance_squared
        wind_x = (
            -2.0
            * self.wind_strength
            * obstacle
            * dx
            * dy
            / distance_squared
        )
        wind_y = self.wind_strength * (
            1.0 + obstacle * (dx * dx - dy * dy) / distance_squared
        )
        front = np.clip(
            -dy / np.maximum(np.hypot(dx, dy), 1.0),
            0.0,
            1.0,
        )
        tip = self._smoothstep((dy - 19.0) / 16.0)
        stretch = 1.0 + 0.3 * (self.tail_flow - 1.0)
        noise_y = y - rear * dy * (1.0 - 1.0 / stretch)
        side_weight = self._smoothstep(
            np.abs(dx) / (13.2 + self.thickness)
        )
        tail_cooling = (1.0 - tip) + tip * 30.0 / self.tail_length
        tail_cooling *= (
            1.0
            + 2.0
            * (1.0 - self.side_tail_ratio)
            * side_weight
            * tip
        )
        return {
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
            "radius": radius,
            "rear": rear,
            "motion": motion,
            "source_radius": source_radius,
            "wind_x": wind_x,
            "wind_y": wind_y,
            "front": front,
            "tip": tip,
            "noise_y": noise_y,
            "tail_cooling": tail_cooling,
        }

    def _split_tail(
        self,
        geometry: dict[str, np.ndarray],
        heat: np.ndarray,
        shape: np.ndarray,
        flicker: np.ndarray,
        detail: np.ndarray,
    ) -> np.ndarray:
        depth = self._smoothstep((geometry["dy"] - 14.0) / 12.0)
        middle_column = max(0, min(self.width - 1, self.width // 2 - 1))
        bend = (
            1.8
            * self.tail_motion
            * (
                0.65 * shape[:, middle_column : middle_column + 1]
                + 0.35 * detail[:, middle_column : middle_column + 1]
            )
            * depth
        )
        notch = np.zeros_like(heat)
        centre_x = (self.width - 1) / 2.0
        for side, offset in ((-1.0, -8.5), (1.0, 8.5)):
            column = max(
                0,
                min(self.width - 1, int(round(centre_x + offset))),
            )
            centre = centre_x + side * self.tail_width * 0.78 + bend
            centre += (
                2.8
                * self.tail_motion
                * shape[:, column : column + 1]
                * depth
            )
            width = 1.2 + 1.6 * depth
            groove = np.exp(-((geometry["x"] - centre) / width) ** 4)
            strength = np.clip(
                0.75 + 1.6 * flicker[:, column : column + 1],
                0.3,
                1.0,
            )
            notch = np.maximum(notch, groove * strength)
        return heat * np.clip(
            1.0 - self.tail_separation * notch * depth,
            0.0,
            1.0,
        ) ** 2

    def _simulate_height(
        self,
        height: int,
    ) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        geometry = self._geometry(height)
        keys = self._make_noise(height)
        heat = np.zeros((height, self.width), dtype=float)
        output: list[tuple[np.ndarray, np.ndarray]] = []
        cycle = self.frames * self._substeps
        for step in range(cycle * 7):
            phase = step % cycle
            key, fraction = divmod(phase, self._substeps)
            blend = self._smoothstep(fraction / self._substeps)
            mixed = (
                keys[key] * (1.0 - blend)
                + keys[(key + 1) % self.frames] * blend
            )
            shape, flow = mixed[:2]
            flicker, detail = [
                self._sample(field, geometry["x"], geometry["noise_y"])
                for field in mixed[2:]
            ]
            gradient_y, gradient_x = np.gradient(flow)
            activity = (
                self.turbulence
                * geometry["motion"]
                * (1.0 + 0.35 * self.tail_chaos * geometry["rear"])
            )
            velocity_x = geometry["wind_x"] + activity * (
                12.0 * gradient_y + 0.85 * detail
            ) / _math.sqrt(self.tail_flow)
            velocity_y = geometry["wind_y"] + activity * (
                -12.0 * gradient_x + 0.6 * flicker
            )
            velocity_y += (
                self.wind_strength
                * (self.tail_flow - 1.0)
                * geometry["rear"]
            )
            downwind_minimum = 0.6 * self.wind_strength * self.tail_flow
            velocity_y = (
                velocity_y * (1.0 - geometry["rear"])
                + np.maximum(velocity_y, downwind_minimum) * geometry["rear"]
            )
            velocity_x += (
                (0.18 + 0.3 * geometry["rear"])
                * geometry["dx"]
                / np.maximum(geometry["radius"], 1.0)
            )
            velocity_y += (
                (0.14 + 0.22 * geometry["rear"])
                * geometry["dy"]
                / np.maximum(geometry["radius"], 1.0)
            )
            transported = self._sample(
                heat,
                geometry["x"] - velocity_x,
                geometry["y"] - velocity_y,
            )
            diffusion = 0.18 * (1.0 - 0.65 * geometry["rear"])
            heat = (
                (1.0 - diffusion) * transported
                + diffusion * self._blur(transported)
            )
            heat -= (
                self.cooling
                * (1.1 + 0.8 * detail)
                * (1.0 + 1.8 * geometry["tip"])
                * geometry["tail_cooling"]
            )
            heat = np.maximum(
                heat,
                self._emitter(geometry, shape, flicker, detail),
            )
            erosion = (
                self.tail_chaos
                * geometry["tip"]
                * np.maximum(detail - 0.05, 0.0)
            )
            heat *= np.clip(1.0 - 0.28 * erosion, 0.25, 1.0)
            heat = self._split_tail(
                geometry,
                heat,
                shape,
                flicker,
                detail,
            )
            heat = np.clip(heat, 0.0, 1.0)
            heat[:2] = 0.0
            heat[:, :2] = heat[:, -2:] = 0.0
            if (
                step >= cycle * 6
                and phase % self._substeps == self._substeps - 1
            ):
                shadow_noise = 0.55 * flicker + 0.35 * shape + 0.25 * detail
                darkness = self._smoothstep((shadow_noise + 0.2) / 0.55)
                shading = 1.0 - self.shadow_strength * darkness
                output.append((heat.copy(), shading))
        return tuple(output)

    def _opacity(self, heat: np.ndarray) -> np.ndarray:
        height, width = heat.shape
        y, x = np.mgrid[:height, :width]
        rear = self._smoothstep((y - 34.0) / 12.0)
        glow = self._blur(heat) * (0.35 - 0.23 * rear)
        density = np.maximum(heat, glow)
        alpha = np.clip(
            (density - (0.045 + 0.065 * rear)) / 0.43,
            0.0,
            1.0,
        ) ** (1.0 + 0.2 * rear)
        edge = np.minimum.reduce([x, y, width - 1 - x])
        return alpha * self._smoothstep((edge - 1.0) / 4.0)

    def simulate(self) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
        """Simulate until every frame's tail has naturally dissipated."""

        if self._states is not None:
            return self._states
        height = max(self.height + 64, self.height * 2)
        while True:
            states = self._simulate_height(height)
            opacity = [self._opacity(heat) for heat, _shading in states]
            if not any(np.any(alpha[-16:]) for alpha in opacity):
                self._last_visible_row = max(
                    int(np.where(alpha > 0.0)[0].max()) for alpha in opacity
                )
                self._states = states
                return states
            height *= 2
            if height > 4096:
                raise ValueError(
                    "Flame tail did not dissipate; increase cooling or reduce "
                    "tail_length/wind_strength"
                )

    def colorize(
        self,
        state: tuple[np.ndarray, np.ndarray],
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> Image.Image:
        """Convert one complete simulated heat state to RGBA."""

        heat, shading = state
        public_color = _color(color)
        colors = (
            self.palette(public_color)
            if palette is None
            else np.asarray(palette, dtype=float)
        )
        if colors.shape != (6, 3) or not np.all(np.isfinite(colors)):
            raise ValueError("Flame palette must contain six finite RGB colours")
        temperature = heat * shading
        rgb = np.stack(
            [
                np.interp(
                    temperature,
                    self._temperature_stops,
                    colors[:, channel],
                )
                for channel in range(3)
            ],
            axis=-1,
        )
        alpha = self._opacity(heat)
        alpha *= np.clip(float(public_color[0]), 0.0, 255.0) / 255.0
        pixels = np.clip(
            np.dstack((rgb, 255.0 * alpha)),
            0.0,
            255.0,
        ).astype(np.uint8)
        pixels[pixels[..., 3] == 0, :3] = 0
        return Image.fromarray(pixels, mode="RGBA")

    def _fit_tail(self, image: Image.Image) -> Image.Image:
        if self._last_visible_row is None:
            raise RuntimeError("Flame must be simulated before fitting its tail")
        target = self.height - 1 - self.margin
        scale = min(
            1.0,
            (target - self.tail_fit_start)
            / max(self._last_visible_row - self.tail_fit_start, 1),
        )
        source_y = np.arange(self.height, dtype=np.float64)
        tail = source_y > self.tail_fit_start
        source_y[tail] = self.tail_fit_start + (
            source_y[tail] - self.tail_fit_start
        ) / scale
        source_y = np.rint(source_y).astype(int)
        source = np.asarray(image)
        result = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        valid = source_y < source.shape[0]
        result[valid] = source[source_y[valid]]
        return Image.fromarray(result, mode="RGBA")

    def render(
        self,
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> list[Image.Image]:
        """Render fitted frames without rotating them or adding a white core."""

        states = self.simulate()
        return [
            self._fit_tail(self.colorize(state, color, palette=palette))
            for state in states
        ]

    def atlas(
        self,
        color: Sequence[ColorChannel],
        palette: Sequence[Sequence[float]] | None = None,
    ) -> Image.Image:
        """Return fitted frames as one horizontal transparent sprite sheet."""

        frames = self.render(color, palette=palette)
        result = Image.new(
            "RGBA",
            (self.width * len(frames), self.height),
            (0, 0, 0, 0),
        )
        for index, frame in enumerate(frames):
            result.alpha_composite(frame, (index * self.width, 0))
        self.image = result
        return result


ProfileFunction = Callable[[float], float]
ProfilePoints = Sequence[Sequence[float]]


class Pottery(Polygon):
    """Deform a shape or a rendered canvas with a one-dimensional profile.

    With ``y_range``, the profile is evaluated along y and changes ``scale_x``.
    With ``x_range``, it is evaluated along x and changes ``scale_y``.  A
    :class:`Canvas` source is captured as a render target and may be saved
    directly with :meth:`save`.
    """

    def __init__(
        self,
        source: Polygon | Circle | Canvas,
        profile: ProfileFunction | ProfilePoints | None = None,
        y_range: Sequence[float] | None = None,
        x_range: Sequence[float] | None = None,
        samples: int = 256,
    ) -> None:
        if not isinstance(source, (Polygon, Circle, Canvas)):
            raise TypeError("Pottery source must be a Polygon, Circle or Canvas")
        if x_range is not None and y_range is not None:
            raise ValueError("Pottery accepts either x_range or y_range, not both")
        if isinstance(samples, bool) or int(samples) < 12:
            raise ValueError("Pottery samples must be an integer of at least 12")
        self.source = source
        self.samples = int(samples)
        self._profile: ProfileFunction | ProfilePoints | None = None
        self._profile_y_range = self._validate_range(y_range, "y_range")
        self._profile_x_range = self._validate_range(x_range, "x_range")
        self._canvas_pixels: np.ndarray | None = None
        self.width: int | None = None
        self.height: int | None = None

        if isinstance(source, Canvas):
            if source._commands:
                image_scale_x = 32.0
                image_scale_y = 32.0
                self.width = source.width * 32
                self.height = source.height * 32
                self._canvas_pixels = source._replay_commands(
                    self.width,
                    self.height,
                )
            else:
                image_scale_x = 1.0
                image_scale_y = 1.0
                self.width = source.width
                self.height = source.height
                self._canvas_pixels = source._pixels.copy()
            half_width = source.width / 2.0
            half_height = source.height / 2.0
            super().__init__(
                [
                    (-half_width, half_height),
                    (half_width, half_height),
                    (half_width, -half_height),
                    (-half_width, -half_height),
                ]
            )
            self.image = Image.fromarray(
                self._deform_canvas(profile, y_range, x_range),
                mode="RGBA",
            )
            self._image_scale_x = image_scale_x
            self._image_scale_y = image_scale_y
        else:
            self._base_points = self._sample_source(source, self.samples)
            positions = self._deformed_positions(profile, y_range, x_range)
            super().__init__(positions)
            self.color = source.color
        self._profile = profile

    @staticmethod
    def _apply_source_transform(
        points: Iterable[tuple[float, float]],
        source: Polygon | Circle,
    ) -> list[tuple[float, float]]:
        radians = _math.radians(source.rot)
        cosine = _math.cos(radians)
        sine = _math.sin(radians)
        transformed: list[tuple[float, float]] = []
        for x, y in points:
            scaled_x = x * source.scale_x
            scaled_y = y * source.scale_y
            transformed.append(
                (
                    scaled_x * cosine - scaled_y * sine,
                    scaled_x * sine + scaled_y * cosine,
                )
            )
        return transformed

    @classmethod
    def _sample_source(
        cls,
        source: Polygon | Circle,
        samples: int,
    ) -> list[tuple[float, float]]:
        if isinstance(source, Circle):
            points = [
                (
                    source.r * _math.cos(2.0 * _math.pi * index / samples),
                    source.r * _math.sin(2.0 * _math.pi * index / samples),
                )
                for index in range(samples)
            ]
            transformed = cls._apply_source_transform(points, source)
            return [
                (x + source.x, y + source.y)
                for x, y in transformed
            ]

        vertices = source.positions
        per_edge = max(1, _math.ceil(samples / len(vertices)))
        points: list[tuple[float, float]] = []
        for index, start in enumerate(vertices):
            end = vertices[(index + 1) % len(vertices)]
            for step in range(per_edge):
                amount = step / per_edge
                points.append(
                    (
                        start[0] + (end[0] - start[0]) * amount,
                        start[1] + (end[1] - start[1]) * amount,
                    )
                )
        return cls._apply_source_transform(points, source)

    @staticmethod
    def _validate_range(
        value: Sequence[float] | None,
        name: str,
    ) -> tuple[float, float] | None:
        if value is None:
            return None
        low, high = _xy(value)
        if not np.isfinite(low) or not np.isfinite(high) or low == high:
            raise ValueError(f"Pottery {name} must contain two different finite values")
        return low, high

    @staticmethod
    def _profile_evaluator(
        profile: ProfileFunction | ProfilePoints | None,
    ) -> ProfileFunction:
        if profile is None:
            return lambda _coordinate: 1.0
        if callable(profile):
            return profile
        controls = sorted((_xy(control) for control in profile), key=lambda item: item[0])
        if not controls:
            raise ValueError("Pottery profile control points cannot be empty")
        control_axis = np.asarray([item[0] for item in controls], dtype=float)
        control_scale = np.asarray([item[1] for item in controls], dtype=float)
        if not np.all(np.isfinite(control_axis)) or not np.all(np.isfinite(control_scale)):
            raise ValueError("Pottery profile control points must be finite")

        def evaluator(coordinate: float) -> float:
            return float(np.interp(coordinate, control_axis, control_scale))

        return evaluator

    def _deformed_positions(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None,
        x_range: Sequence[float] | None,
    ) -> list[tuple[float, float]]:
        if x_range is not None and y_range is not None:
            raise ValueError("Pottery accepts either x_range or y_range, not both")
        vertical_deformation = x_range is not None
        semantic_range = self._validate_range(
            x_range if vertical_deformation else y_range,
            "x_range" if vertical_deformation else "y_range",
        )
        source_axis = [
            x if vertical_deformation else y for x, y in self._base_points
        ]
        source_min = min(source_axis)
        source_max = max(source_axis)
        source_span = source_max - source_min
        evaluator = self._profile_evaluator(profile)

        result: list[tuple[float, float]] = []
        for x, y in self._base_points:
            source_coordinate = x if vertical_deformation else y
            profile_coordinate = source_coordinate
            if semantic_range is not None:
                amount = (
                    0.0
                    if source_span == 0.0
                    else (source_coordinate - source_min) / source_span
                )
                profile_coordinate = semantic_range[0] + amount * (
                    semantic_range[1] - semantic_range[0]
                )
            deformation_scale = float(evaluator(profile_coordinate))
            if not np.isfinite(deformation_scale) or deformation_scale < 0.0:
                raise ValueError("Pottery profile scales must be non-negative finite numbers")
            if vertical_deformation:
                result.append((x, y * deformation_scale))
            else:
                result.append((x * deformation_scale, y))
        return result

    def _deform_canvas(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None,
        x_range: Sequence[float] | None,
    ) -> np.ndarray:
        if self._canvas_pixels is None or self.width is None or self.height is None:
            raise TypeError("canvas deformation requires a Canvas source")
        if x_range is not None and y_range is not None:
            raise ValueError("Pottery accepts either x_range or y_range, not both")

        vertical_deformation = x_range is not None
        semantic_range = self._validate_range(
            x_range if vertical_deformation else y_range,
            "x_range" if vertical_deformation else "y_range",
        )
        evaluator = self._profile_evaluator(profile)
        alpha = self._canvas_pixels[..., 3]
        occupied_rows, occupied_columns = np.nonzero(alpha)
        if occupied_rows.size == 0:
            return np.zeros_like(self._canvas_pixels)

        if vertical_deformation:
            axis_coordinates = (
                np.arange(self.width, dtype=float) + 0.5 - self.width / 2.0
            )
            occupied_axis = axis_coordinates[np.unique(occupied_columns)]
        else:
            axis_coordinates = (
                self.height / 2.0
                - (np.arange(self.height, dtype=float) + 0.5)
            )
            occupied_axis = axis_coordinates[np.unique(occupied_rows)]
        source_min = float(occupied_axis.min())
        source_max = float(occupied_axis.max())
        source_span = source_max - source_min
        inside = (axis_coordinates >= source_min) & (axis_coordinates <= source_max)
        scales = np.zeros_like(axis_coordinates)
        for index in np.nonzero(inside)[0]:
            profile_coordinate = float(axis_coordinates[index])
            if semantic_range is not None:
                amount = (
                    0.5
                    if source_span == 0.0
                    else (axis_coordinates[index] - source_min) / source_span
                )
                profile_coordinate = semantic_range[0] + amount * (
                    semantic_range[1] - semantic_range[0]
                )
            scale = float(evaluator(profile_coordinate))
            if not np.isfinite(scale) or scale < 0.0:
                raise ValueError("Pottery profile scales must be non-negative finite numbers")
            scales[index] = scale

        columns, rows = np.meshgrid(
            np.arange(self.width, dtype=float),
            np.arange(self.height, dtype=float),
        )
        logical_x = columns + 0.5 - self.width / 2.0
        logical_y = self.height / 2.0 - (rows + 0.5)
        if vertical_deformation:
            scale_grid = scales[None, :]
            source_columns = columns
            source_rows = np.divide(
                logical_y,
                scale_grid,
                out=np.full_like(logical_y, np.nan),
                where=scale_grid > 1e-12,
            )
            source_rows = self.height / 2.0 - source_rows - 0.5
        else:
            scale_grid = scales[:, None]
            source_rows = rows
            source_columns = np.divide(
                logical_x,
                scale_grid,
                out=np.full_like(logical_x, np.nan),
                where=scale_grid > 1e-12,
            )
            source_columns = source_columns + self.width / 2.0 - 0.5

        valid = (
            np.isfinite(source_rows)
            & np.isfinite(source_columns)
            & (source_rows >= 0.0)
            & (source_rows <= self.height - 1)
            & (source_columns >= 0.0)
            & (source_columns <= self.width - 1)
        )
        safe_rows = np.where(valid, source_rows, 0.0)
        safe_columns = np.where(valid, source_columns, 0.0)
        row0 = np.floor(safe_rows).astype(int)
        column0 = np.floor(safe_columns).astype(int)
        row1 = np.minimum(row0 + 1, self.height - 1)
        column1 = np.minimum(column0 + 1, self.width - 1)
        row_amount = safe_rows - row0
        column_amount = safe_columns - column0

        source = self._canvas_pixels.astype(float) / 255.0
        source[..., :3] *= source[..., 3:4]
        top = (
            source[row0, column0] * (1.0 - column_amount[..., None])
            + source[row0, column1] * column_amount[..., None]
        )
        bottom = (
            source[row1, column0] * (1.0 - column_amount[..., None])
            + source[row1, column1] * column_amount[..., None]
        )
        sampled = (
            top * (1.0 - row_amount[..., None])
            + bottom * row_amount[..., None]
        )
        sampled[~valid] = 0.0
        output_alpha = sampled[..., 3:4]
        output_rgb = np.divide(
            sampled[..., :3],
            output_alpha,
            out=np.zeros_like(sampled[..., :3]),
            where=output_alpha > 0.0,
        )
        output = np.concatenate((output_rgb, output_alpha), axis=2)
        return np.clip(np.rint(output * 255.0), 0, 255).astype(np.uint8)

    def set_profile(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None = None,
        x_range: Sequence[float] | None = None,
    ) -> "Pottery":
        """Replace the active profile and rebuild the geometry or image."""

        if x_range is not None and y_range is not None:
            raise ValueError("Pottery accepts either x_range or y_range, not both")
        if self._canvas_pixels is not None:
            self.image = Image.fromarray(
                self._deform_canvas(profile, y_range, x_range),
                mode="RGBA",
            )
        else:
            self.positions = self._deformed_positions(profile, y_range, x_range)
        self._profile = profile
        self._profile_y_range = self._validate_range(y_range, "y_range")
        self._profile_x_range = self._validate_range(x_range, "x_range")
        return self

    def save(
        self,
        path: str | Path,
        multiplier: float = 1,
        multiplier_y: float | None = None,
    ) -> Path:
        """Save a canvas-backed Pottery render target."""

        if self._canvas_pixels is None or self.image is None:
            raise TypeError("save is available when Pottery was created from a Canvas")
        scale_x = float(multiplier)
        scale_y = scale_x if multiplier_y is None else float(multiplier_y)
        if (
            not np.isfinite(scale_x)
            or not np.isfinite(scale_y)
            or scale_x <= 0.0
            or scale_y <= 0.0
        ):
            raise ValueError("multipliers must be positive finite numbers")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image = self.image.copy()
        if self.rot % 360.0 != 0.0:
            image = (
                image.convert("RGBa")
                .rotate(
                    self.rot,
                    resample=Image.Resampling.BILINEAR,
                    expand=False,
                    fillcolor=(0, 0, 0, 0),
                )
                .convert("RGBA")
            )
        image_scale_x = getattr(self, "_image_scale_x", 1.0)
        image_scale_y = getattr(self, "_image_scale_y", 1.0)
        if (
            scale_x != image_scale_x
            or scale_y != image_scale_y
        ):
            image = (
                image.convert("RGBa")
                .resize(
                    (
                        max(1, round(image.width * scale_x / image_scale_x)),
                        max(1, round(image.height * scale_y / image_scale_y)),
                    ),
                    Image.Resampling.HAMMING,
                )
                .convert("RGBA")
            )
        pixels = np.asarray(image, dtype=np.uint8).copy()
        pixels[pixels[..., 3] == 0, :3] = 0
        Image.fromarray(pixels, mode="RGBA").save(destination)
        return destination


class Stretch(Pottery):
    """Apply a same-axis local stretch field to a shape or rendered canvas.

    ``x_range`` makes ``scale_x`` vary with x; ``y_range`` makes ``scale_y``
    vary with y.  The profile is treated as a local derivative and integrated
    into a monotonic coordinate mapping, preventing folds and overlaps.
    """

    def __init__(
        self,
        source: Polygon | Circle | Canvas,
        profile: ProfileFunction | ProfilePoints | None = None,
        y_range: Sequence[float] | None = None,
        x_range: Sequence[float] | None = None,
        samples: int = 256,
    ) -> None:
        if (x_range is None) == (y_range is None):
            raise ValueError("Stretch requires exactly one of x_range or y_range")
        super().__init__(
            source,
            profile=profile,
            y_range=y_range,
            x_range=x_range,
            samples=samples,
        )

    def _integrated_mapping(
        self,
        source_min: float,
        source_max: float,
        profile: ProfileFunction | ProfilePoints | None,
        semantic_range: tuple[float, float],
    ) -> tuple[np.ndarray, np.ndarray]:
        source_span = source_max - source_min
        count = max(1025, int(_math.ceil(abs(source_span) * 8.0)) + 1)
        source_axis = np.linspace(source_min, source_max, count)
        semantic_axis = semantic_range[0] + (
            (source_axis - source_min) / source_span
        ) * (semantic_range[1] - semantic_range[0])
        evaluator = self._profile_evaluator(profile)
        local_scale = np.asarray(
            [float(evaluator(float(coordinate))) for coordinate in semantic_axis],
            dtype=float,
        )
        if not np.all(np.isfinite(local_scale)) or np.any(local_scale <= 0.0):
            raise ValueError("Stretch profile scales must be positive finite numbers")

        mapped_axis = np.zeros_like(source_axis)
        mapped_axis[1:] = np.cumsum(
            (local_scale[:-1] + local_scale[1:])
            * 0.5
            * np.diff(source_axis)
        )
        if 0.0 < source_min:
            mapped_origin = mapped_axis[0] - source_min * local_scale[0]
        elif 0.0 > source_max:
            mapped_origin = mapped_axis[-1] + (0.0 - source_max) * local_scale[-1]
        else:
            mapped_origin = float(np.interp(0.0, source_axis, mapped_axis))
        mapped_axis -= mapped_origin
        return source_axis, mapped_axis

    def _deformed_positions(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None,
        x_range: Sequence[float] | None,
    ) -> list[tuple[float, float]]:
        if (x_range is None) == (y_range is None):
            raise ValueError("Stretch requires exactly one of x_range or y_range")
        horizontal = x_range is not None
        semantic_range = self._validate_range(
            x_range if horizontal else y_range,
            "x_range" if horizontal else "y_range",
        )
        assert semantic_range is not None
        source_values = [x if horizontal else y for x, y in self._base_points]
        source_axis, mapped_axis = self._integrated_mapping(
            min(source_values),
            max(source_values),
            profile,
            semantic_range,
        )
        result: list[tuple[float, float]] = []
        for x, y in self._base_points:
            if horizontal:
                result.append((float(np.interp(x, source_axis, mapped_axis)), y))
            else:
                result.append((x, float(np.interp(y, source_axis, mapped_axis))))
        return result

    def _deform_canvas(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None,
        x_range: Sequence[float] | None,
    ) -> np.ndarray:
        if self._canvas_pixels is None or self.width is None or self.height is None:
            raise TypeError("canvas deformation requires a Canvas source")
        if (x_range is None) == (y_range is None):
            raise ValueError("Stretch requires exactly one of x_range or y_range")

        horizontal = x_range is not None
        semantic_range = self._validate_range(
            x_range if horizontal else y_range,
            "x_range" if horizontal else "y_range",
        )
        assert semantic_range is not None
        alpha = self._canvas_pixels[..., 3]
        occupied_rows, occupied_columns = np.nonzero(alpha)
        if occupied_rows.size == 0:
            return np.zeros_like(self._canvas_pixels)

        if horizontal:
            output_axis = (
                np.arange(self.width, dtype=float) + 0.5 - self.width / 2.0
            )
            occupied_axis = output_axis[np.unique(occupied_columns)]
        else:
            output_axis = (
                self.height / 2.0
                - (np.arange(self.height, dtype=float) + 0.5)
            )
            occupied_axis = output_axis[np.unique(occupied_rows)]
        source_axis, mapped_axis = self._integrated_mapping(
            float(occupied_axis.min()),
            float(occupied_axis.max()),
            profile,
            semantic_range,
        )
        valid_axis = (
            (output_axis >= mapped_axis[0])
            & (output_axis <= mapped_axis[-1])
        )
        source_coordinates = np.interp(output_axis, mapped_axis, source_axis)

        source = self._canvas_pixels.astype(float) / 255.0
        source[..., :3] *= source[..., 3:4]
        if horizontal:
            source_indices = source_coordinates + self.width / 2.0 - 0.5
            index0 = np.floor(source_indices).astype(int)
            index0 = np.clip(index0, 0, self.width - 1)
            index1 = np.minimum(index0 + 1, self.width - 1)
            amount = source_indices - index0
            sampled = (
                source[:, index0] * (1.0 - amount[None, :, None])
                + source[:, index1] * amount[None, :, None]
            )
            sampled[:, ~valid_axis] = 0.0
        else:
            source_indices = self.height / 2.0 - source_coordinates - 0.5
            index0 = np.floor(source_indices).astype(int)
            index0 = np.clip(index0, 0, self.height - 1)
            index1 = np.minimum(index0 + 1, self.height - 1)
            amount = source_indices - index0
            sampled = (
                source[index0, :] * (1.0 - amount[:, None, None])
                + source[index1, :] * amount[:, None, None]
            )
            sampled[~valid_axis, :] = 0.0

        output_alpha = sampled[..., 3:4]
        output_rgb = np.divide(
            sampled[..., :3],
            output_alpha,
            out=np.zeros_like(sampled[..., :3]),
            where=output_alpha > 0.0,
        )
        output = np.concatenate((output_rgb, output_alpha), axis=2)
        return np.clip(np.rint(output * 255.0), 0, 255).astype(np.uint8)

    def set_profile(
        self,
        profile: ProfileFunction | ProfilePoints | None,
        y_range: Sequence[float] | None = None,
        x_range: Sequence[float] | None = None,
    ) -> "Stretch":
        if (x_range is None) == (y_range is None):
            raise ValueError("Stretch requires exactly one of x_range or y_range")
        super().set_profile(profile, y_range=y_range, x_range=x_range)
        return self


Boundary = Polygon | Circle
Shape = Point | Boundary


class Canvas:
    """An RGBA canvas whose logical origin is at its centre.

    Logical x grows rightwards and logical y grows upwards.  ``put`` associates
    a shape with an offset.  Gradient operations use those stored offsets.
    """

    def __init__(
        self,
        width: int,
        height: int,
        interpolation_mode: str = "r",
    ) -> None:
        if isinstance(width, bool) or isinstance(height, bool):
            raise TypeError("canvas dimensions must be integers")
        self.width = int(width)
        self.height = int(height)
        if self.width <= 0 or self.height <= 0:
            raise ValueError("canvas dimensions must be positive")
        self._pixels = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        self._placements: dict[Shape, tuple[float, float]] = {}
        self._interpolation_origin = (0.0, 0.0)
        self._rot = 0.0
        self._interpolation_mode = "r"
        # Drawing still happens immediately at one pixel per logical unit so
        # callers can inspect/use the canvas.  Public operations are also
        # recorded and can be replayed at the final output density by save().
        self._commands: list[tuple[object, ...]] = []
        self._record_enabled = True
        self.interpolation_mode = interpolation_mode

    @staticmethod
    def _copy_shape_style(source: Shape, target: Shape) -> Shape:
        target.color = source.color
        if isinstance(source, (Polygon, Circle)) and isinstance(
            target, (Polygon, Circle)
        ):
            target.scale_x = source.scale_x
            target.scale_y = source.scale_y
            target.rot = source.rot
        return target

    def _snapshot_shape(self, shape: Shape) -> Shape:
        """Copy a shape exactly as positioned for the current operation."""

        if isinstance(shape, Point):
            x, y = self._logical_vertices(shape)[0]
            return self._copy_shape_style(shape, Point(x, y))
        if isinstance(shape, Polygon):
            # Bake placement, scale and rotation into the vertices.  Later
            # edits to the user's object cannot alter an earlier draw command.
            result = Polygon(self._logical_vertices(shape))
            result.color = shape.color
            return result
        centre_x, centre_y = self._circle_centre(shape)
        return self._copy_shape_style(
            shape,
            Circle(shape.r, centre_x, centre_y),
        )

    @staticmethod
    def _scale_shape(shape: Shape, scale_x: float, scale_y: float) -> Shape:
        """Map a snapshotted logical shape into output pixel coordinates."""

        if isinstance(shape, Point):
            result: Shape = Point(shape.x * scale_x, shape.y * scale_y)
            result.color = shape.color
            return result
        if isinstance(shape, Polygon):
            result = Polygon(
                [
                    (x * scale_x, y * scale_y)
                    for x, y in shape.positions
                ]
            )
            result.color = shape.color
            return result

        # A non-uniform output scale applied to a rotated ellipse is still an
        # ellipse.  SVD recovers its exact output radii and orientation.
        radians = _math.radians(shape.rot)
        cosine = _math.cos(radians)
        sine = _math.sin(radians)
        local_to_output = np.asarray(
            [
                [
                    scale_x * cosine * shape.r * shape.scale_x,
                    -scale_x * sine * shape.r * shape.scale_y,
                ],
                [
                    scale_y * sine * shape.r * shape.scale_x,
                    scale_y * cosine * shape.r * shape.scale_y,
                ],
            ],
            dtype=float,
        )
        axes, radii, _basis = np.linalg.svd(local_to_output)
        if np.linalg.det(axes) < 0.0:
            axes[:, 1] *= -1.0
        result = Circle(
            1.0,
            shape.x * scale_x,
            shape.y * scale_y,
        )
        result.scale_x = float(radii[0])
        result.scale_y = float(radii[1])
        result.rot = _math.degrees(_math.atan2(axes[1, 0], axes[0, 0]))
        result.color = shape.color
        return result

    @staticmethod
    def _snapshot_image_shape(shape: Boundary) -> Boundary:
        if isinstance(shape, Polygon):
            result: Boundary = Polygon(shape.positions)
        else:
            result = Circle(shape.r, shape.x, shape.y)
        result.color = shape.color
        result.scale_x = shape.scale_x
        result.scale_y = shape.scale_y
        result.rot = shape.rot
        result.image = None if shape.image is None else shape.image.copy()
        result._image_scale_x = getattr(shape, "_image_scale_x", 1.0)
        result._image_scale_y = getattr(shape, "_image_scale_y", 1.0)
        return result

    @staticmethod
    def _scale_image_shape(
        shape: Boundary,
        scale_x: float,
        scale_y: float,
    ) -> Boundary:
        result = Canvas._snapshot_image_shape(shape)
        if result.image is not None:
            image_scale_x = getattr(result, "_image_scale_x", 1.0)
            image_scale_y = getattr(result, "_image_scale_y", 1.0)
            result.image = (
                result.image.convert("RGBa")
                .resize(
                    (
                        max(1, round(result.image.width * scale_x / image_scale_x)),
                        max(1, round(result.image.height * scale_y / image_scale_y)),
                    ),
                    Image.Resampling.HAMMING,
                )
                .convert("RGBA")
            )
            result._image_scale_x = 1.0
            result._image_scale_y = 1.0
        return result

    def _replay_commands(
        self,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Replay public drawing operations directly at the requested size."""

        scale_x = width / self.width
        scale_y = height / self.height
        target = Canvas(width, height, self.interpolation_mode)
        target._record_enabled = False
        for command in self._commands:
            operation = command[0]
            if operation == "solid_fill":
                _operation, boundary, blend_mode = command
                target.fill_color(
                    self._scale_shape(boundary, scale_x, scale_y),
                    blend_mode=str(blend_mode),
                )
            elif operation == "fill":
                (
                    _operation,
                    inner,
                    outer,
                    method,
                    blend_mode,
                    interpolation_mode,
                    origin,
                ) = command
                target.interpolation_mode = str(interpolation_mode)
                target._interpolation_origin = (
                    float(origin[0]) * scale_x,
                    float(origin[1]) * scale_y,
                )
                target.fill_color(
                    self._scale_shape(inner, scale_x, scale_y),
                    self._scale_shape(outer, scale_x, scale_y),
                    str(method),
                    str(blend_mode),
                )
            elif operation == "shade_edge":
                (
                    _operation,
                    boundary,
                    color,
                    radius,
                    method,
                    region,
                ) = command
                scaled_region = (
                    None
                    if region is None
                    else self._scale_shape(region, scale_x, scale_y)
                )
                target.shade_edge(
                    self._scale_shape(boundary, scale_x, scale_y),
                    color,
                    float(radius) * _math.sqrt(scale_x * scale_y),
                    str(method),
                    region=scaled_region,
                )
            elif operation == "cut":
                _operation, boundary, side = command
                target.cut(
                    self._scale_shape(boundary, scale_x, scale_y),
                    str(side),
                )
            elif operation == "image":
                _operation, shape, position = command
                target.put(
                    self._scale_image_shape(shape, scale_x, scale_y),
                    float(position[0]) * scale_x,
                    float(position[1]) * scale_y,
                )
        return target._pixels.copy()

    def _rasterize_commands(
        self,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Rasterize with the original zoom=32 supersampling convention.

        An axis exported at its logical size or larger is replayed internally
        at 32 pixels per logical unit.  An axis already supplied at a larger
        legacy resolution and exported smaller is kept at its existing raster
        density, preventing a second 32x expansion.
        """

        raster_width = self.width * 32 if width >= self.width else self.width
        raster_height = self.height * 32 if height >= self.height else self.height
        sampled = self._replay_commands(raster_width, raster_height)
        if (raster_width, raster_height) == (width, height):
            return sampled
        # Match the old Canvas(high_resolution).save(..., 1/zoom) path:
        # resolve premultiplied RGBA with Pillow's Hamming filter.
        resolved = (
            Image.fromarray(sampled, mode="RGBA")
            .convert("RGBa")
            .resize((width, height), Image.Resampling.HAMMING)
            .convert("RGBA")
        )
        pixels = np.asarray(resolved, dtype=np.uint8).copy()
        pixels[pixels[..., 3] == 0, :3] = 0
        return pixels

    @property
    def rot(self) -> float:
        return self._rot

    @rot.setter
    def rot(self, value: float) -> None:
        self._rot = _angle(value)

    @property
    def interpolation_mode(self) -> str:
        return self._interpolation_mode

    @interpolation_mode.setter
    def interpolation_mode(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("interpolation_mode must be a string")
        key = value.strip().lower()
        if key not in {"r", "w", "h"}:
            raise ValueError("interpolation_mode must be 'r', 'w' or 'h'")
        self._interpolation_mode = key

    def set_origin(self, origin: Point) -> None:
        """Set the interpolation origin used by subsequent fills.

        The point's current ``put`` offset is included.  Changing the origin
        does not alter pixels rasterized by earlier ``fill_color`` calls.
        """

        if not isinstance(origin, Point):
            raise TypeError("set_origin expects a point")
        self._interpolation_origin = self._logical_vertices(origin)[0]

    def put(
        self,
        shape: Shape,
        x: float | Sequence[float],
        y: float | None = None,
    ) -> Shape:
        if not isinstance(shape, (Point, Polygon, Circle)):
            raise TypeError("shape must be a point, Polygon or Circle")
        if y is None:
            if isinstance(x, (str, bytes)) or not isinstance(x, Sequence):
                raise TypeError("put expects x, y or a two-item tuple/list")
            position = _xy(x)
        else:
            if isinstance(x, Sequence):
                raise TypeError("when y is provided, x must be a number")
            position = (float(x), float(y))
        self._placements[shape] = position
        if isinstance(shape, (Polygon, Circle)) and shape.image is not None:
            self._composite_image_shape(shape, position)
            if self._record_enabled:
                self._commands.append(
                    (
                        "image",
                        self._snapshot_image_shape(shape),
                        position,
                    )
                )
        return shape

    def _composite_image_shape(
        self,
        shape: Boundary,
        position: tuple[float, float],
    ) -> None:
        """Alpha-composite an image-backed shape at a logical position."""

        if shape.image is None:
            return
        image = shape.image.copy()
        image_scale_x = getattr(shape, "_image_scale_x", 1.0)
        image_scale_y = getattr(shape, "_image_scale_y", 1.0)
        resize_x = shape.scale_x / image_scale_x
        resize_y = shape.scale_y / image_scale_y
        if resize_x != 1.0 or resize_y != 1.0:
            image = (
                image.convert("RGBa")
                .resize(
                    (
                        max(1, round(image.width * resize_x)),
                        max(1, round(image.height * resize_y)),
                    ),
                    Image.Resampling.BILINEAR,
                )
                .convert("RGBA")
            )
        if shape.rot % 360.0 != 0.0:
            image = (
                image.convert("RGBa")
                .rotate(
                    shape.rot,
                    resample=Image.Resampling.BILINEAR,
                    expand=True,
                    fillcolor=(0, 0, 0, 0),
                )
                .convert("RGBA")
            )

        logical_x, logical_y = position
        left = round(self.width / 2.0 + logical_x - image.width / 2.0)
        top = round(self.height / 2.0 - logical_y - image.height / 2.0)
        destination_left = max(0, left)
        destination_top = max(0, top)
        destination_right = min(self.width, left + image.width)
        destination_bottom = min(self.height, top + image.height)
        if destination_left >= destination_right or destination_top >= destination_bottom:
            return

        source_left = destination_left - left
        source_top = destination_top - top
        source_right = source_left + destination_right - destination_left
        source_bottom = source_top + destination_bottom - destination_top
        source = np.asarray(
            image.crop((source_left, source_top, source_right, source_bottom)),
            dtype=np.uint8,
        )
        source_mask = source[..., 3] > 0
        source_rows, source_columns = np.nonzero(source_mask)
        if source_rows.size == 0:
            return
        self._blend_pixels(
            source_rows + destination_top,
            source_columns + destination_left,
            source[source_mask].astype(float),
            "alpha",
        )

    def _logical_vertices(self, shape: Point | Polygon) -> list[tuple[float, float]]:
        dx, dy = self._placements.get(shape, (0.0, 0.0))
        if isinstance(shape, Point):
            return [(shape.x + dx, shape.y + dy)]
        radians = _math.radians(shape.rot)
        cosine = _math.cos(radians)
        sine = _math.sin(radians)
        vertices: list[tuple[float, float]] = []
        for x, y in shape.positions:
            scaled_x = x * shape.scale_x
            scaled_y = y * shape.scale_y
            vertices.append(
                (
                    scaled_x * cosine - scaled_y * sine + dx,
                    scaled_x * sine + scaled_y * cosine + dy,
                )
            )
        return vertices

    def _circle_centre(self, circle: Circle) -> tuple[float, float]:
        dx, dy = self._placements.get(circle, (0.0, 0.0))
        return circle.x + dx, circle.y + dy

    def _screen(self, vertex: tuple[float, float]) -> tuple[float, float]:
        x, y = vertex
        return self.width / 2.0 + x, self.height / 2.0 - y

    def _polygon_mask(self, polygon: Polygon) -> np.ndarray:
        mask_image = Image.new("L", (self.width, self.height), 0)
        vertices = [
            self._screen(vertex) for vertex in self._logical_vertices(polygon)
        ]
        draw = ImageDraw.Draw(mask_image)
        if len(vertices) == 2:
            draw.line(vertices, fill=255, width=1)
        else:
            draw.polygon(vertices, fill=255)
        return np.asarray(mask_image, dtype=np.uint8) != 0

    def _between_lines_mask(self, first: Polygon, second: Polygon) -> np.ndarray:
        """Return the area spanned between two zero-width line segments."""

        first_vertices = self._logical_vertices(first)
        second_vertices = self._logical_vertices(second)
        direct = sum(
            (first_vertices[index][0] - second_vertices[index][0]) ** 2
            + (first_vertices[index][1] - second_vertices[index][1]) ** 2
            for index in range(2)
        )
        crossed = sum(
            (first_vertices[index][0] - second_vertices[1 - index][0]) ** 2
            + (first_vertices[index][1] - second_vertices[1 - index][1]) ** 2
            for index in range(2)
        )
        if crossed < direct:
            second_vertices.reverse()
        bridge = [
            first_vertices[0],
            second_vertices[0],
            second_vertices[1],
            first_vertices[1],
        ]
        mask_image = Image.new("L", (self.width, self.height), 0)
        ImageDraw.Draw(mask_image).polygon(
            [self._screen(vertex) for vertex in bridge],
            fill=255,
        )
        return np.asarray(mask_image, dtype=np.uint8) != 0

    def _shape_mask(self, shape: Boundary) -> np.ndarray:
        if isinstance(shape, Polygon):
            return self._polygon_mask(shape)
        logical_centre_x, logical_centre_y = self._circle_centre(shape)
        centre_x = self.width / 2.0 + logical_centre_x
        centre_y = self.height / 2.0 - logical_centre_y
        radius_x = shape.r * shape.scale_x
        radius_y = shape.r * shape.scale_y
        radians = _math.radians(shape.rot)
        cosine = _math.cos(radians)
        sine = _math.sin(radians)
        extent_x = _math.hypot(radius_x * cosine, radius_y * sine)
        extent_y = _math.hypot(radius_x * sine, radius_y * cosine)

        # Preserve the original Circle rasterization convention.  Pillow's
        # ellipse bounding box is inclusive at its far edge, which gives the
        # old zoom=32 output its half-pixel outer coverage after reduction.
        # The analytical pixel-centre test below is still needed for a truly
        # rotated ellipse; circles and axis-aligned ellipses use the legacy
        # path exactly.
        if abs(_math.sin(2.0 * radians)) <= 1e-12:
            mask_image = Image.new("L", (self.width, self.height), 0)
            ImageDraw.Draw(mask_image).ellipse(
                (
                    centre_x - extent_x,
                    centre_y - extent_y,
                    centre_x + extent_x,
                    centre_y + extent_y,
                ),
                fill=255,
            )
            return np.asarray(mask_image, dtype=np.uint8) != 0

        min_column = max(0, int(_math.floor(centre_x - extent_x)))
        max_column = min(self.width - 1, int(_math.ceil(centre_x + extent_x)))
        min_row = max(0, int(_math.floor(centre_y - extent_y)))
        max_row = min(self.height - 1, int(_math.ceil(centre_y + extent_y)))
        mask = np.zeros((self.height, self.width), dtype=bool)
        if min_column > max_column or min_row > max_row:
            return mask

        columns, rows = np.meshgrid(
            np.arange(min_column, max_column + 1, dtype=float) + 0.5,
            np.arange(min_row, max_row + 1, dtype=float) + 0.5,
        )
        relative_x = columns - self.width / 2.0 - logical_centre_x
        relative_y = self.height / 2.0 - rows - logical_centre_y
        local_x = cosine * relative_x + sine * relative_y
        local_y = -sine * relative_x + cosine * relative_y
        mask[min_row : max_row + 1, min_column : max_column + 1] = (
            (local_x / radius_x) ** 2 + (local_y / radius_y) ** 2 <= 1.0
        )
        return mask

    @staticmethod
    def _radial_limit(
        vertices: Sequence[tuple[float, float]],
        centre: tuple[float, float],
        direction_x: np.ndarray,
        direction_y: np.ndarray,
    ) -> np.ndarray:
        """Return the polygon intersection radius for each ray direction."""

        result = np.full(direction_x.shape, np.inf, dtype=float)
        centre_x, centre_y = centre
        relative = [(x - centre_x, y - centre_y) for x, y in vertices]
        for index, (start_x, start_y) in enumerate(relative):
            end_x, end_y = relative[(index + 1) % len(relative)]
            edge_x = end_x - start_x
            edge_y = end_y - start_y
            denominator = direction_x * edge_y - direction_y * edge_x
            with np.errstate(divide="ignore", invalid="ignore"):
                radius = (start_x * edge_y - start_y * edge_x) / denominator
                segment = (start_x * direction_y - start_y * direction_x) / denominator
            valid = (
                (np.abs(denominator) > 1e-12)
                & (radius >= 0.0)
                & (segment >= -1e-9)
                & (segment <= 1.0 + 1e-9)
            )
            result = np.where(valid & (radius < result), radius, result)
        return result

    def _shape_radial_limit(
        self,
        shape: Boundary,
        centre: tuple[float, float],
        direction_x: np.ndarray,
        direction_y: np.ndarray,
    ) -> np.ndarray:
        if isinstance(shape, Polygon):
            return self._radial_limit(
                self._logical_vertices(shape),
                centre,
                direction_x,
                direction_y,
            )

        centre_x, centre_y = self._circle_centre(shape)
        ray_centre_x, ray_centre_y = centre
        centre_x -= ray_centre_x
        centre_y -= ray_centre_y
        radius_x = shape.r * shape.scale_x
        radius_y = shape.r * shape.scale_y
        radians = _math.radians(shape.rot)
        cosine = _math.cos(radians)
        sine = _math.sin(radians)
        local_direction_x = cosine * direction_x + sine * direction_y
        local_direction_y = -sine * direction_x + cosine * direction_y
        local_centre_x = cosine * centre_x + sine * centre_y
        local_centre_y = -sine * centre_x + cosine * centre_y
        inverse_x2 = 1.0 / radius_x**2
        inverse_y2 = 1.0 / radius_y**2
        coefficient_a = (
            local_direction_x**2 * inverse_x2
            + local_direction_y**2 * inverse_y2
        )
        coefficient_b = -2.0 * (
            local_direction_x * local_centre_x * inverse_x2
            + local_direction_y * local_centre_y * inverse_y2
        )
        coefficient_c = (
            local_centre_x**2 * inverse_x2
            + local_centre_y**2 * inverse_y2
            - 1.0
        )
        discriminant = coefficient_b**2 - 4.0 * coefficient_a * coefficient_c
        valid = discriminant >= 0.0
        with np.errstate(divide="ignore", invalid="ignore"):
            root = (
                -coefficient_b + np.sqrt(np.maximum(discriminant, 0.0))
            ) / (2.0 * coefficient_a)
        return np.where(valid & (root >= 0.0), root, np.inf)

    def _blend_pixels(
        self,
        rows: np.ndarray,
        columns: np.ndarray,
        source: np.ndarray,
        mode: str,
    ) -> None:
        """Blend RGBA source samples into the selected canvas pixels."""

        destination = self._pixels[rows, columns].astype(float)
        if mode == "replace":
            result = source
        elif mode == "alpha":
            source_normalized = source / 255.0
            destination_normalized = destination / 255.0
            source_alpha = source_normalized[:, 3:4]
            destination_alpha = destination_normalized[:, 3:4]
            output_alpha = source_alpha + destination_alpha * (1.0 - source_alpha)
            premultiplied_rgb = (
                source_normalized[:, :3] * source_alpha
                + destination_normalized[:, :3]
                * destination_alpha
                * (1.0 - source_alpha)
            )
            output_rgb = np.divide(
                premultiplied_rgb,
                output_alpha,
                out=np.zeros_like(premultiplied_rgb),
                where=output_alpha > 0.0,
            )
            result = np.concatenate((output_rgb, output_alpha), axis=1) * 255.0
        elif mode == "add":
            result = destination + source
        elif mode == "sub":
            result = destination - source
        else:  # mul
            result = destination * source / 255.0
        self._pixels[rows, columns] = np.clip(np.rint(result), 0, 255).astype(np.uint8)

    def _fill_between_shapes_radially(
        self,
        inner: Shape,
        outer: Boundary,
        blend_mode: str,
        interpolation_power: float,
        interpolation_subtract: bool,
    ) -> None:
        """Interpolate shapes along rays emitted from the canvas origin."""

        centre = self._interpolation_origin
        if isinstance(inner, Point):
            inner_mask = np.zeros((self.height, self.width), dtype=bool)
        else:
            inner_mask = self._shape_mask(inner)
        outer_mask = self._shape_mask(outer)
        if (
            isinstance(inner, Polygon)
            and len(inner.positions) == 2
            and isinstance(outer, Polygon)
            and len(outer.positions) == 2
        ):
            ring = self._between_lines_mask(inner, outer)
        else:
            ring = outer_mask & ~inner_mask
        rows, columns = np.nonzero(ring)
        if rows.size == 0:
            return

        logical_x = columns.astype(float) + 0.5 - self.width / 2.0
        logical_y = self.height / 2.0 - (rows.astype(float) + 0.5)
        offset_x = logical_x - centre[0]
        offset_y = logical_y - centre[1]
        radius = np.hypot(offset_x, offset_y)
        if self.interpolation_mode == "w":
            # Width interpolation advances independently to the left and
            # right of the first interpolation point.  Per-row limits make
            # the gradient follow pottery profiles and other outlines.
            x_coordinates = (
                np.arange(self.width, dtype=float)[None, :]
                + 0.5
                - self.width / 2.0
            )
            relative_x = x_coordinates - centre[0]
            outer_positive = np.max(
                np.where(outer_mask & (relative_x >= 0.0), relative_x, -np.inf),
                axis=1,
            )
            outer_negative = np.max(
                np.where(outer_mask & (relative_x <= 0.0), -relative_x, -np.inf),
                axis=1,
            )
            if isinstance(inner, Point):
                inner_positive = np.zeros(self.height, dtype=float)
                inner_negative = np.zeros(self.height, dtype=float)
            else:
                inner_positive = np.max(
                    np.where(inner_mask & (relative_x >= 0.0), relative_x, -np.inf),
                    axis=1,
                )
                inner_negative = np.max(
                    np.where(inner_mask & (relative_x <= 0.0), -relative_x, -np.inf),
                    axis=1,
                )
                inner_positive[~np.isfinite(inner_positive)] = 0.0
                inner_negative[~np.isfinite(inner_negative)] = 0.0
            positive_side = offset_x >= 0.0
            inner_limit = np.where(
                positive_side,
                inner_positive[rows],
                inner_negative[rows],
            )
            outer_limit = np.where(
                positive_side,
                outer_positive[rows],
                outer_negative[rows],
            )
            span = outer_limit - inner_limit
            amount = np.divide(
                np.abs(offset_x) - inner_limit,
                span,
                out=np.ones_like(logical_x),
                where=np.isfinite(span) & (np.abs(span) > 1e-12),
            )
        elif self.interpolation_mode == "h":
            # Height interpolation uses the recorded point's y coordinate
            # and advances independently towards the top and bottom.
            y_coordinates = (
                self.height / 2.0
                - (np.arange(self.height, dtype=float)[:, None] + 0.5)
            )
            relative_y = y_coordinates - centre[1]
            outer_positive = np.max(
                np.where(outer_mask & (relative_y >= 0.0), relative_y, -np.inf),
                axis=0,
            )
            outer_negative = np.max(
                np.where(outer_mask & (relative_y <= 0.0), -relative_y, -np.inf),
                axis=0,
            )
            if isinstance(inner, Point):
                inner_positive = np.zeros(self.width, dtype=float)
                inner_negative = np.zeros(self.width, dtype=float)
            else:
                inner_positive = np.max(
                    np.where(inner_mask & (relative_y >= 0.0), relative_y, -np.inf),
                    axis=0,
                )
                inner_negative = np.max(
                    np.where(inner_mask & (relative_y <= 0.0), -relative_y, -np.inf),
                    axis=0,
                )
                inner_positive[~np.isfinite(inner_positive)] = 0.0
                inner_negative[~np.isfinite(inner_negative)] = 0.0
            positive_side = offset_y >= 0.0
            inner_limit = np.where(
                positive_side,
                inner_positive[columns],
                inner_negative[columns],
            )
            outer_limit = np.where(
                positive_side,
                outer_positive[columns],
                outer_negative[columns],
            )
            span = outer_limit - inner_limit
            amount = np.divide(
                np.abs(offset_y) - inner_limit,
                span,
                out=np.ones_like(logical_y),
                where=np.isfinite(span) & (np.abs(span) > 1e-12),
            )
        else:
            direction_x = np.divide(
                offset_x,
                radius,
                out=np.zeros_like(offset_x),
                where=radius != 0,
            )
            direction_y = np.divide(
                offset_y,
                radius,
                out=np.zeros_like(offset_y),
                where=radius != 0,
            )
            if isinstance(inner, Point):
                inner_limit = np.zeros_like(radius)
            else:
                inner_limit = self._shape_radial_limit(
                    inner, centre, direction_x, direction_y
                )
            outer_limit = self._shape_radial_limit(
                outer, centre, direction_x, direction_y
            )
            span = outer_limit - inner_limit
            amount = np.divide(
                radius - inner_limit,
                span,
                out=np.ones_like(radius),
                where=np.isfinite(span) & (np.abs(span) > 1e-12),
            )
        amount = np.clip(amount, 0.0, 1.0)
        if self.interpolation_mode == "r":
            amount[radius <= 1e-12] = 0.0
        if interpolation_subtract:
            amount = 1.0 - (1.0 - amount) ** interpolation_power
        elif interpolation_power != 1.0:
            amount = amount**interpolation_power
        inner_rgba = np.asarray(_rgba(inner.color), dtype=float)
        outer_rgba = np.asarray(_rgba(outer.color), dtype=float)
        colors = (1.0 - amount[:, None]) * inner_rgba + amount[:, None] * outer_rgba
        self._blend_pixels(rows, columns, colors, blend_mode)

    def _paint_triangle(
        self,
        vertices: Sequence[tuple[float, float]],
        colors: Sequence[Color],
    ) -> None:
        screen = np.asarray([self._screen(vertex) for vertex in vertices], dtype=float)
        min_x = max(0, int(np.floor(screen[:, 0].min())))
        max_x = min(self.width - 1, int(np.ceil(screen[:, 0].max())))
        min_y = max(0, int(np.floor(screen[:, 1].min())))
        max_y = min(self.height - 1, int(np.ceil(screen[:, 1].max())))
        if min_x > max_x or min_y > max_y:
            return

        a, b, c = screen
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-12:
            return
        grid_x, grid_y = np.meshgrid(
            np.arange(min_x, max_x + 1, dtype=float) + 0.5,
            np.arange(min_y, max_y + 1, dtype=float) + 0.5,
        )
        w0 = ((b[1] - c[1]) * (grid_x - c[0]) + (c[0] - b[0]) * (grid_y - c[1])) / denominator
        w1 = ((c[1] - a[1]) * (grid_x - c[0]) + (a[0] - c[0]) * (grid_y - c[1])) / denominator
        w2 = 1.0 - w0 - w1
        mask = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not np.any(mask):
            return

        rgba = (
            w0[..., None] * np.asarray(_rgba(colors[0]), dtype=float)
            + w1[..., None] * np.asarray(_rgba(colors[1]), dtype=float)
            + w2[..., None] * np.asarray(_rgba(colors[2]), dtype=float)
        )
        region = self._pixels[min_y : max_y + 1, min_x : max_x + 1]
        region[mask] = np.clip(np.rint(rgba[mask]), 0, 255).astype(np.uint8)

    def fill_color(
        self,
        inner: Shape,
        outer: Boundary | str | None = None,
        method: str = "lerp",
        blend_mode: str = "replace",
    ) -> None:
        """Fill one closed shape, or interpolate from *inner* to *outer*.

        With only *inner*, it must be a :class:`Circle` or a closed
        :class:`Polygon` of at least three points.  Its complete interior is
        filled with ``inner.color``.  With *outer*, the existing two-shape
        interpolation behaviour is used.  For a single shape,
        ``fill_color(shape, "alpha")`` is shorthand for
        ``fill_color(shape, blend_mode="alpha")``.

        The interpolation origin defaults to ``(0, 0)`` and can be changed
        explicitly with :meth:`set_origin`.  An *inner* point supplies the
        starting colour but does not implicitly change that origin.

        ``method`` accepts ``"lerp"`` or ``"1"`` for linear interpolation,
        and any positive numeric exponent followed by ``"add"`` or ``"sub"``
        (for example ``"1.564sub"``).  ``blend_mode`` may be
        ``"replace"``, ``"alpha"``, ``"add"``, ``"sub"`` or ``"mul"``.
        The public ARGB colours are converted to RGBA only for raster blending.
        """

        if isinstance(outer, str):
            if method != "lerp" or blend_mode != "replace":
                raise TypeError(
                    "the positional blend-mode shorthand cannot be combined "
                    "with method or blend_mode"
                )
            blend_mode = outer
            outer = None

        blend_mode = blend_mode.lower()
        if blend_mode not in {"replace", "alpha", "add", "sub", "mul"}:
            raise ValueError("blend_mode must be 'replace', 'alpha', 'add', 'sub' or 'mul'")

        if outer is None:
            if not isinstance(inner, (Polygon, Circle)):
                raise TypeError(
                    "single-object fill_color expects a closed Polygon or Circle"
                )
            if isinstance(inner, Polygon) and len(inner.positions) < 3:
                raise ValueError(
                    "single-object fill_color cannot fill an open line segment"
                )
            rows, columns = np.nonzero(self._shape_mask(inner))
            if rows.size:
                rgba = np.asarray(_rgba(inner.color), dtype=float)
                source = np.broadcast_to(rgba, (rows.size, 4))
                self._blend_pixels(rows, columns, source, blend_mode)
            if self._record_enabled:
                self._commands.append(
                    (
                        "solid_fill",
                        self._snapshot_shape(inner),
                        blend_mode,
                    )
                )
            return

        method_key = method.strip().lower()
        interpolation_subtract = False
        if method_key in {"lerp", "1"}:
            interpolation_power = 1.0
        else:
            if method_key.endswith("add"):
                power_text = method_key[:-3]
            elif method_key.endswith("sub"):
                power_text = method_key[:-3]
                interpolation_subtract = True
            else:
                raise ValueError(
                    "method must be 'lerp', '1', or a positive number followed by 'add' or 'sub'"
                )
            try:
                interpolation_power = float(power_text)
            except ValueError as error:
                raise ValueError(
                    "the interpolation exponent must be a positive number"
                ) from error
            if not np.isfinite(interpolation_power) or interpolation_power <= 0.0:
                raise ValueError("the interpolation exponent must be a positive finite number")
        if not isinstance(inner, (Point, Polygon, Circle)) or not isinstance(outer, (Polygon, Circle)):
            raise TypeError("fill_color expects a point, Polygon or Circle, then a Polygon or Circle")

        self._fill_between_shapes_radially(
            inner,
            outer,
            blend_mode,
            interpolation_power,
            interpolation_subtract,
        )
        if self._record_enabled:
            self._commands.append(
                (
                    "fill",
                    self._snapshot_shape(inner),
                    self._snapshot_shape(outer),
                    method,
                    blend_mode,
                    self.interpolation_mode,
                    self._interpolation_origin,
                )
            )

    def shade_edge(
        self,
        boundary: Boundary,
        color: Sequence[ColorChannel],
        radius: float,
        method: str = "lerp",
        region: Boundary | None = None,
    ) -> None:
        """Tint a shape inward from its actual outer boundary.

        The effect follows convex, concave and curved boundary segments as one
        continuous field.  Connections inside a compound silhouette are not
        treated as edges.  Only RGB is tinted; existing pixel alpha is kept,
        so the method can safely be applied after opacity gradients.

        ``radius`` is measured in canvas pixels.  ``method`` accepts the same
        interpolation syntax as :meth:`fill_color`.  An optional ``region``
        limits where the tint is applied without changing which outline is
        used to calculate the continuous edge field.
        """

        if not isinstance(boundary, (Polygon, Circle)):
            raise TypeError("boundary must be a Polygon or Circle")
        if isinstance(boundary, Polygon) and len(boundary.positions) == 2:
            raise ValueError("a line segment has no inside edge to shade")
        if region is not None:
            if not isinstance(region, (Polygon, Circle)):
                raise TypeError("region must be a Polygon or Circle")
            if isinstance(region, Polygon) and len(region.positions) == 2:
                raise ValueError("a line segment cannot be used as a region")
        numeric_radius = float(radius)
        if not np.isfinite(numeric_radius) or numeric_radius <= 0.0:
            raise ValueError("radius must be a positive finite number")

        method_key = method.strip().lower()
        interpolation_subtract = False
        if method_key in {"lerp", "1"}:
            interpolation_power = 1.0
        else:
            if method_key.endswith("add"):
                power_text = method_key[:-3]
            elif method_key.endswith("sub"):
                power_text = method_key[:-3]
                interpolation_subtract = True
            else:
                raise ValueError(
                    "method must be 'lerp', '1', or a positive number followed by 'add' or 'sub'"
                )
            try:
                interpolation_power = float(power_text)
            except ValueError as error:
                raise ValueError(
                    "the interpolation exponent must be a positive number"
                ) from error
            if not np.isfinite(interpolation_power) or interpolation_power <= 0.0:
                raise ValueError(
                    "the interpolation exponent must be a positive finite number"
                )

        public_color = _color(color)
        if self._record_enabled:
            self._commands.append(
                (
                    "shade_edge",
                    self._snapshot_shape(boundary),
                    public_color,
                    numeric_radius,
                    method,
                    None if region is None else self._snapshot_shape(region),
                )
            )
        mask = self._shape_mask(boundary)
        distance = _inside_distance_field(mask)
        amount = np.clip(1.0 - distance / numeric_radius, 0.0, 1.0)
        if interpolation_subtract:
            amount = 1.0 - (1.0 - amount) ** interpolation_power
        elif interpolation_power != 1.0:
            amount = amount**interpolation_power

        rgba = np.asarray(_rgba(public_color), dtype=float)
        strength = amount * np.clip(rgba[3] / 255.0, 0.0, 1.0)
        active = mask & (self._pixels[..., 3] > 0) & (strength > 0.0)
        if region is not None:
            active &= self._shape_mask(region)
        if not np.any(active):
            return
        destination = self._pixels[..., :3].astype(float)
        result = (
            destination[active] * (1.0 - strength[active, None])
            + np.clip(rgba[:3], 0.0, 255.0) * strength[active, None]
        )
        self._pixels[active, :3] = np.clip(
            np.rint(result),
            0,
            255,
        ).astype(np.uint8)

    def cut(self, boundary: Boundary, side: str = "out") -> Boundary:
        """Make pixels outside (or inside) *boundary* transparent.

        The canvas is changed in place.  A shape carrying a snapshot in its
        ``image`` attribute is returned for callers that want the cut result.
        """

        if not isinstance(boundary, (Polygon, Circle)):
            raise TypeError("boundary must be a Polygon or Circle")
        if isinstance(boundary, Polygon) and len(boundary.positions) == 2:
            raise ValueError("a line segment has no inside or outside and cannot be cut")
        side = side.lower()
        if side not in {"out", "in"}:
            raise ValueError("side must be 'out' or 'in'")

        mask = self._shape_mask(boundary)
        if side == "out":
            self._pixels[~mask] = 0
        else:
            self._pixels[mask] = 0
        if self._record_enabled:
            self._commands.append(
                (
                    "cut",
                    self._snapshot_shape(boundary),
                    side,
                )
            )

        result: Boundary
        if isinstance(boundary, Polygon):
            result = Polygon(boundary.positions)
        else:
            result = Circle(boundary.r, boundary.x, boundary.y)
        result.color = boundary.color
        result.scale_x = boundary.scale_x
        result.scale_y = boundary.scale_y
        result.rot = boundary.rot
        result.image = Image.fromarray(self._pixels.copy(), mode="RGBA")
        return result

    def render(
        self,
        multiplier: float = 1,
        multiplier_y: float | None = None,
    ) -> Image.Image:
        """Rasterize the logical canvas and return an RGBA image.

        The canvas dimensions and every geometry coordinate are logical units.
        With one multiplier, the same pixel density is applied horizontally
        and vertically.  With two multipliers, the first controls horizontal
        density and the second vertical density.  Public drawing commands are
        replayed internally with ``zoom=32`` and then resolved to the target
        size with premultiplied RGBA Hamming filtering.  An already-rasterized
        low-resolution image is never enlarged to implement the multiplier.
        """

        scale_x = float(multiplier)
        scale_y = scale_x if multiplier_y is None else float(multiplier_y)
        if (
            not np.isfinite(scale_x)
            or not np.isfinite(scale_y)
            or scale_x <= 0
            or scale_y <= 0
        ):
            raise ValueError("multipliers must be positive finite numbers")
        size = (
            max(1, round(self.width * scale_x)),
            max(1, round(self.height * scale_y)),
        )
        if self._commands:
            pixels = self._rasterize_commands(*size)
        elif size == (self.width, self.height):
            pixels = self._pixels.copy()
        else:
            # A canvas changed only through its private pixel array has no
            # logical operations to replay.  Keep a safe compatibility path
            # for such internal render targets.
            fallback = (
                Image.fromarray(self._pixels, mode="RGBA")
                .convert("RGBa")
                .resize(size, Image.Resampling.HAMMING)
                .convert("RGBA")
            )
            pixels = np.asarray(fallback, dtype=np.uint8).copy()
        image = Image.fromarray(pixels, mode="RGBA")
        if self.rot % 360.0 != 0.0:
            image = (
                image.convert("RGBa")
                .rotate(
                    self.rot,
                    resample=Image.Resampling.BILINEAR,
                    expand=False,
                    fillcolor=(0, 0, 0, 0),
                )
                .convert("RGBA")
            )
        rendered = np.asarray(image, dtype=np.uint8).copy()
        rendered[rendered[..., 3] == 0, :3] = 0
        return Image.fromarray(rendered, mode="RGBA")

    def save(
        self,
        path: str | Path,
        multiplier: float = 1,
        multiplier_y: float | None = None,
    ) -> Path:
        """Rasterize the logical canvas and save it as an RGBA image."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image = self.render(multiplier, multiplier_y)
        image.save(destination)
        return destination


__all__ = [
    "Canvas",
    "Circle",
    "Flame",
    "Implicit",
    "Point",
    "Polygon",
    "Pottery",
    "RadialScale",
    "Stretch",
    "point",
]
