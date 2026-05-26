import os
import pickle
from collections import Counter
from collections.abc import Iterable
from typing import Any

import matplotlib.colors as mcolors
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.path import Path

import pandas as pd

NODE_WIDTH: int = 11
MIN_CONTAINER_HEIGHT: int = 3
MAX_CONTAINER_HEIGHT: int = 10
ROW_GAP: int = 0


def scale_range(
    value: float,
    input_min: float,
    input_max: float,
    output_min: float,
    output_max: float,
) -> float:
    """Scale a value from one range into another.

    Parameters
    ----------
    value : float
        Value to scale.
    input_min : float
        Minimum input range value.
    input_max : float
        Maximum input range value.
    output_min : float
        Minimum output range value.
    output_max : float
        Maximum output range value.

    Returns
    -------
    float
        Scaled value.

    Examples
    --------
    >>> scale_range(5, 0, 10, 0, 100)
    50.0
    """
    if input_min == input_max:
        # PSS: Prevent division by zero.
        return output_min

    return (
        (value - input_min) * (output_max - output_min) / (input_max - input_min)
    ) + output_min


def hide_axis_spines(axis: plt.Axes) -> None:
    """Hide the top and right spines of a Matplotlib axis.

    Parameters
    ----------
    axis : matplotlib.axes.Axes
        Axis where the spines will be hidden.

    Returns
    -------
    None
    """
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)


def draw_bezier_flow(
    axis: plt.Axes,
    source_x: float,
    target_x: float,
    source_y: float,
    source_height: float,
    target_y: float,
    target_height: float,
    color: str,
    alpha: float = 0.35,
) -> None:
    """Draw a Bézier flow between two Sankey nodes.

    Parameters
    ----------
    axis : matplotlib.axes.Axes
        Matplotlib axis.
    source_x : float
        Source x coordinate.
    target_x : float
        Target x coordinate.
    source_y : float
        Source y coordinate.
    source_height : float
        Height of the source flow.
    target_y : float
        Target y coordinate.
    target_height : float
        Height of the target flow.
    color : str
        Flow color.
    alpha : float, optional
        Flow transparency.
    """
    vertices = [
        (source_x, source_y),
        (
            source_x + (target_x - source_x) / 2,
            source_y,
        ),
        (
            source_x + (target_x - source_x) / 2,
            target_y,
        ),
        (target_x, target_y),
        (target_x, target_y - target_height),
        (
            source_x + (target_x - source_x) / 2,
            target_y - target_height,
        ),
        (
            source_x + (target_x - source_x) / 2,
            source_y - source_height,
        ),
        (source_x, source_y - source_height),
        (source_x, source_y),
    ]

    path_codes = [
        Path.MOVETO,
        Path.CURVE4,
        Path.CURVE4,
        Path.CURVE4,
        Path.LINETO,
        Path.CURVE4,
        Path.CURVE4,
        Path.CURVE4,
        Path.CLOSEPOLY,
    ]

    bezier_path = Path(vertices, path_codes)

    axis.add_patch(
        patches.PathPatch(
            bezier_path,
            facecolor=color,
            edgecolor="none",
            alpha=alpha,
        )
    )


def precompute_global_heights(
    trace_histories: list[list[str]],
    tool_names: list[str],
    step_columns: list[str],
) -> tuple[
    dict[str, float],
    dict[str, float],
    float,
]:
    """Precompute consistent row heights across all columns.

    Parameters
    ----------
    trace_histories : list[list[str]]
        List of tool execution sequences.
    tool_names : list[str]
        Available tool names.
    step_columns : list[str]
        Sankey column labels.

    Returns
    -------
    tuple
        (
            row_base_positions,
            max_row_heights,
            total_height,
        )
    """
    node_usage_stats: dict[
        tuple[str, str],
        dict[str, int],
    ] = {}

    for column_name in step_columns:
        for tool_name in tool_names:
            node_usage_stats[(column_name, tool_name)] = {
                "outputs": 0,
                "inputs": 0,
            }

    flow_data: Counter[Any] = Counter()

    for sequence in trace_histories:
        effective_steps = min(
            len(sequence),
            len(step_columns),
        )

        for index in range(effective_steps - 1):
            flow_data[
                (
                    step_columns[index],
                    sequence[index],
                    step_columns[index + 1],
                    sequence[index + 1],
                )
            ] += 1

    if not flow_data:
        # PSS: Added protection for empty datasets.
        return {}, {}, 0

    max_flow_value = max(flow_data.values())
    min_flow_value = min(flow_data.values())

    for column_name in step_columns:
        for tool_name in tool_names:
            output_count = sum(
                count
                for (
                    source_column,
                    source_tool,
                    _,
                    _,
                ), count in flow_data.items()
                if source_column == column_name and source_tool == tool_name
            )

            input_count = sum(
                count
                for (
                    _,
                    _,
                    target_column,
                    target_tool,
                ), count in flow_data.items()
                if target_column == column_name and target_tool == tool_name
            )

            node_usage_stats[(column_name, tool_name)] = {
                "outputs": output_count,
                "inputs": input_count,
            }

    max_row_heights: dict[str, float] = {}

    for tool_name in tool_names:
        cell_values = []

        for column_name in step_columns:
            flow_value = (
                node_usage_stats[(column_name, tool_name)]["outputs"]
                if column_name == step_columns[0]
                else node_usage_stats[(column_name, tool_name)]["inputs"]
            )

            scaled_value = scale_range(
                flow_value,
                min_flow_value,
                max_flow_value,
                MIN_CONTAINER_HEIGHT,
                MAX_CONTAINER_HEIGHT,
            )

            cell_values.append(scaled_value)

        max_row_heights[tool_name] = max(cell_values)

    row_base_positions: dict[str, float] = {}
    accumulated_y = 0

    for tool_name in reversed(tool_names):
        row_base_positions[tool_name] = accumulated_y

        accumulated_y += max_row_heights[tool_name] + ROW_GAP

    return (
        row_base_positions,
        max_row_heights,
        accumulated_y + 0,
    )


def draw_sankey_on_axis(
    axis: plt.Axes,
    trace_sequences: list[list[str]],
    tool_names: list[str],
    step_columns: list[str],
    color_palette: dict[str, str],
    chart_title: str,
    row_base_positions: dict[str, float],
    max_row_heights: dict[str, float],
    global_max_height: float,
    font_color: str = "#1F2937",
) -> None:
    """Render a Sankey diagram on a Matplotlib axis."""
    column_positions = {
        column_name: index * 16 for index, column_name in enumerate(step_columns)
    }

    flow_data: Counter[Any] = Counter()

    for sequence in trace_sequences:
        effective_steps = min(
            len(sequence),
            len(step_columns),
        )

        for index in range(effective_steps - 1):
            flow_data[
                (
                    step_columns[index],
                    sequence[index],
                    step_columns[index + 1],
                    sequence[index + 1],
                )
            ] += 1

    if not flow_data:
        return

    max_flow_value = max(flow_data.values())
    min_flow_value = min(flow_data.values())

    node_usage: dict[
        tuple[str, str],
        dict[str, float],
    ] = {}

    for column_name in step_columns:
        for tool_name in tool_names:
            output_count = sum(
                count
                for (
                    source_column,
                    source_tool,
                    _,
                    _,
                ), count in flow_data.items()
                if source_column == column_name and source_tool == tool_name
            )

            input_count = sum(
                count
                for (
                    _,
                    _,
                    target_column,
                    target_tool,
                ), count in flow_data.items()
                if target_column == column_name and target_tool == tool_name
            )

            container_height = (
                output_count if column_name == step_columns[0] else input_count
            )

            container_height = scale_range(
                container_height,
                min_flow_value,
                max_flow_value,
                MIN_CONTAINER_HEIGHT,
                MAX_CONTAINER_HEIGHT,
            )

            node_usage[(column_name, tool_name)] = {
                "outputs": output_count,
                "inputs": input_count,
                "container_height": container_height,
            }

    node_coordinates: dict[
        tuple[str, str],
        dict[str, float],
    ] = {}

    for column_name in step_columns:
        x_position = column_positions[column_name]

        for tool_name in tool_names:
            row_base_y = row_base_positions[tool_name] - 3

            row_max_height = max_row_heights[tool_name]

            container_height = node_usage[(column_name, tool_name)]["container_height"]

            container_base_y = row_base_y + (row_max_height - container_height) / 2

            usage_data = node_usage[(column_name, tool_name)]

            is_used = usage_data["inputs"] > 0 or usage_data["outputs"] > 0

            if is_used:
                background_rect = plt.Rectangle(
                    (
                        x_position - NODE_WIDTH / 2,
                        container_base_y,
                    ),
                    NODE_WIDTH,
                    container_height,
                    color="#D1D5DB",
                    alpha=0.4,
                    zorder=1,
                )

                axis.add_patch(background_rect)

                tool_color = color_palette.get(
                    tool_name,
                    "#999999",
                )

                colored_rect = plt.Rectangle(
                    (
                        x_position - NODE_WIDTH / 2,
                        container_base_y,
                    ),
                    NODE_WIDTH,
                    container_height,
                    color=tool_color,
                    alpha=0.85,
                    zorder=2,
                )

                axis.add_patch(colored_rect)

            node_coordinates[(column_name, tool_name)] = {
                "x": x_position,
                "top_y": (container_base_y + container_height),
                "height": (container_height if is_used else 0),
                "output_accumulator": 0,
                "input_accumulator": 0,
            }

            center_y = row_base_y + row_max_height / 2

            if is_used:
                axis.text(
                    x_position,
                    center_y,
                    tool_name,
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=font_color,
                    zorder=3,
                )

    for (
        source_column,
        source_tool,
        target_column,
        target_tool,
    ), flow_value in flow_data.items():
        source_key = (
            source_column,
            source_tool,
        )

        target_key = (
            target_column,
            target_tool,
        )

        source_node = node_coordinates[source_key]
        target_node = node_coordinates[target_key]

        total_source_flow = (
            node_usage[source_key]["outputs"]
            if source_column == step_columns[0]
            else node_usage[source_key]["inputs"]
        )

        total_target_flow = node_usage[target_key]["inputs"]

        source_flow_height = (
            (flow_value / total_source_flow) * source_node["height"]
            if total_source_flow > 0
            else 0
        )

        target_flow_height = (
            (flow_value / total_target_flow) * target_node["height"]
            if total_target_flow > 0
            else 0
        )

        source_y = source_node["top_y"] - source_node["output_accumulator"]

        target_y = target_node["top_y"] - target_node["input_accumulator"]

        flow_color = color_palette.get(
            source_tool,
            "#999999",
        )

        draw_bezier_flow(
            axis=axis,
            source_x=(source_node["x"] + NODE_WIDTH / 2),
            target_x=(target_node["x"] - NODE_WIDTH / 2),
            source_y=source_y,
            source_height=source_flow_height,
            target_y=target_y,
            target_height=target_flow_height,
            color=flow_color,
        )

        source_node["output_accumulator"] += source_flow_height

        target_node["input_accumulator"] += target_flow_height

    axis.set_xlim(
        -NODE_WIDTH,
        max(column_positions.values()) + NODE_WIDTH,
    )

    axis.set_ylim(
        -5,
        global_max_height + 5,
    )

    for (
        column_name,
        x_position,
    ) in column_positions.items():
        axis.text(
            x_position,
            global_max_height,
            column_name,
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color="#111827",
            alpha=0.5,
        )

    axis.set_title(
        chart_title,
        fontsize=20,
        fontweight="bold",
        color="#919191",
        pad=10,
    )

    axis.axis("off")


def plot_steps(
    figure: plt.Figure,
    planning_traces: list[list[str]],
    validation_traces: list[list[str]],
    color_map_name: str = "tab10",
    font_color: str = "#1F2937",
) -> None:
    """Plot planning and validation Sankey diagrams."""
    color_map = plt.get_cmap(color_map_name)

    planning_steps = [
        f"STEP-{index}"
        for index in range(
            1,
            1 + max(len(trace) for trace in planning_traces),
        )
    ]

    planning_tools = ["Logic"] + list(
        {tool for trace in planning_traces for tool in trace}
    )

    planning_palette = {
        tool_name: mcolors.to_hex(color_map(index))
        for index, tool_name in enumerate(planning_tools)
    }

    (
        planning_positions,
        planning_heights,
        planning_max_height,
    ) = precompute_global_heights(
        planning_traces,
        planning_tools,
        planning_steps,
    )

    planning_axis = figure.add_subplot(211)

    draw_sankey_on_axis(
        axis=planning_axis,
        trace_sequences=planning_traces,
        tool_names=planning_tools,
        step_columns=planning_steps,
        color_palette=planning_palette,
        chart_title="PLANIFICATION",
        row_base_positions=planning_positions,
        max_row_heights=planning_heights,
        global_max_height=planning_max_height,
        font_color=font_color,
    )

    validation_steps = [
        f"STEP-{index}"
        for index in range(
            1,
            1 + max(len(trace) for trace in validation_traces),
        )
    ]

    validation_tools = ["Logic"] + list(
        {tool for trace in validation_traces for tool in trace}
    )

    validation_palette = {
        tool_name: mcolors.to_hex(color_map(index))
        for index, tool_name in enumerate(validation_tools)
    }

    (
        validation_positions,
        validation_heights,
        validation_max_height,
    ) = precompute_global_heights(
        validation_traces,
        validation_tools,
        validation_steps,
    )

    validation_axis = figure.add_subplot(212)

    draw_sankey_on_axis(
        axis=validation_axis,
        trace_sequences=validation_traces,
        tool_names=validation_tools,
        step_columns=validation_steps,
        color_palette=validation_palette,
        chart_title="VALIDATION",
        row_base_positions=validation_positions,
        max_row_heights=validation_heights,
        global_max_height=validation_max_height,
        font_color=font_color,
    )


def filter_structures(
    trace_data: list[list[str]],
    threshold: float = 0.95,
) -> list[list[str]]:
    """Filter structures according to frequency.

    Parameters
    ----------
    trace_data : list[list[str]]
        Trace sequences.
    threshold : float, optional
        Preserve the most frequent trajectories until covering at least `threshold` of all traces.

    Returns
    -------
    list[list[str]]
        Filtered traces.
    """
    if not trace_data:
        return []

    structure_counts = Counter(tuple(trace_sequence) for trace_sequence in trace_data)

    total_traces = len(trace_data)
    sorted_structures = structure_counts.most_common()
    selected_structures: set[tuple[str, ...]] = set()
    cumulative_probability = 0.0

    for structure, count in sorted_structures:
        probability = count / total_traces
        selected_structures.add(structure)
        cumulative_probability += probability
        if cumulative_probability >= threshold:
            break

    return [
        trace_sequence
        for trace_sequence in trace_data
        if tuple(trace_sequence) in selected_structures
    ]


def get_plot_data(
    trace_files: list[str],
    threshold: float = 0.95,
) -> tuple[
    list[list[str]],
    list[list[str]],
]:
    """Load and preprocess Sankey trace data.

    Parameters
    ----------
    trace_files : list[str]
        Trace file names.
    base_path : str
        Directory path.
    threshold : float, optional
        Frequency filter threshold.

    Returns
    -------
    tuple[list[list[str]], list[list[str]]]
        Planning and validation traces.
    """
    traces: list[Any] = []

    for trace_file in trace_files:

        if not os.path.exists(trace_file):
            raise FileNotFoundError(f"File not found: {trace_file}")

        with open(trace_file, "rb") as file:
            traces.append(pickle.load(file))

    def normalize_tool_name(
        tool_name: str,
    ) -> str:
        """Normalize tool names."""
        return tool_name.replace("_", " ").capitalize()

    planning_sequences: list[list[str]] = []
    validation_sequences: list[list[str]] = []

    for trace in traces:
        planning_steps: list[str] = []
        validation_steps: list[str] = []

        for trace_item in trace["trace"]:
            planning_steps.extend(
                [
                    normalize_tool_name(item.tool)
                    for item in trace_item["solution_trace"]
                ]
            )

            validation_steps.extend(
                [
                    normalize_tool_name(item.tool)
                    for item in trace_item["verification_trace"]
                ]
            )

        planning_sequences.append(planning_steps)

        validation_sequences.append(validation_steps)

    # PSS: Replaced filter/lambda with clearer comprehensions.
    planning_sequences = [
        sequence for sequence in planning_sequences if len(sequence) > 2
    ]

    validation_sequences = [
        sequence for sequence in validation_sequences if len(sequence) > 2
    ]

    planning_sequences = filter_structures(
        planning_sequences,
        threshold,
    )

    validation_sequences = filter_structures(
        validation_sequences,
        threshold,
    )

    return (
        planning_sequences,
        validation_sequences,
    )


def count_trace_frequencies(
    trace_sequences: Iterable[Iterable[Any]],
) -> tuple[list[str], list[float]]:
    """Count repeated trace sequences and compute relative frequencies.

    Parameters
    ----------
    trace_sequences : Iterable[Iterable[Any]]
        Collection of trace sequences to analyze.

    Returns
    -------
    tuple[list[str], list[float]]
        A tuple containing:
        - A list of trace labels.
        - A list of relative frequencies in percentage.
    """
    trace_frequency_counter = Counter(
        tuple(trace_sequence) for trace_sequence in trace_sequences
    )

    sorted_trace_frequencies = trace_frequency_counter.most_common()

    trace_labels = [
        f"Path {index + 1}" for index in range(len(sorted_trace_frequencies))
    ]

    absolute_frequencies = [
        frequency_count for _, frequency_count in sorted_trace_frequencies
    ]

    total_frequency_count = sum(absolute_frequencies)

    relative_frequencies = [
        (100 * frequency_count / total_frequency_count)
        for frequency_count in absolute_frequencies
    ]

    return (
        trace_labels,
        relative_frequencies,
    )


def draw_trace_frequency_bars(
    figure: Any,
    trace_datasets: tuple[
        Iterable[Iterable[Any]],
        Iterable[Iterable[Any]],
    ],
) -> None:
    """Draw bar charts for planning and validation trace frequencies.

    Parameters
    ----------
    figure : Any
        Figure-like object containing the subplot method.
    trace_datasets : tuple[
        Iterable[Iterable[Any]],
        Iterable[Iterable[Any]],
    ]
        Tuple containing:
        - Planning trace data.
        - Validation trace data.

    Returns
    -------
    None
    """
    if len(trace_datasets) != 2:
        msg = "trace_datasets must contain exactly " "two datasets."
        raise ValueError(msg)

    planning_trace_sequences, validation_trace_sequences = trace_datasets

    # PSS: Renamed subplot variables and functions
    # to preserve Sankey/trace visualization context.

    # Plot planning trace frequencies.
    planning_axis = figure.add_subplot(121)
    hide_axis_spines(planning_axis)

    plt.grid(
        True,
        zorder=-1,
    )

    (
        planning_trace_labels,
        planning_trace_percentages,
    ) = count_trace_frequencies(planning_trace_sequences)

    plt.bar(
        planning_trace_labels,
        planning_trace_percentages,
        zorder=99,
        color="C0",
    )

    plt.title("Planning trace frequencies")
    plt.ylabel("Percentage (%)")

    # Plot validation trace frequencies.
    validation_axis = figure.add_subplot(122)
    hide_axis_spines(validation_axis)

    plt.grid(
        True,
        zorder=-1,
    )

    (
        validation_trace_labels,
        validation_trace_percentages,
    ) = count_trace_frequencies(validation_trace_sequences)

    plt.bar(
        validation_trace_labels,
        validation_trace_percentages,
        zorder=99,
        color="C1",
    )

    plt.title("Validation trace frequencies")


def get_execution_metrics(trace_file_paths: list[str]) -> dict[str, list[int]]:
    """Extract execution metrics from trace files.

    Parameters
    ----------
    trace_file_paths : list[str]
        List of file paths containing serialized trace data.

    Returns
    -------
    dict[str, list[int]]
        Dictionary containing:
        - attempts: Number of attempts per task.
        - solutions: Number of solution steps per task.
        - verifications: Number of verification steps per task.
    """
    execution_metrics = {
        "attempts": [],
        "solutions": [],
        "verifications": [],
    }

    processed_tracks = 0

    for trace_file_path in trace_file_paths:
        with open(trace_file_path, "rb") as file:
            trace_data = pickle.load(file)

        if not trace_data["trace"]:
            print(f"Empty trace found: {trace_file_path}")
            continue

        processed_tracks += 1

        execution_summary = trace_data["trace"][0]["execution_summary"]

        solution_count = 0
        verification_count = 0

        for attempt_id in execution_summary:
            attempt_data = execution_summary[attempt_id]

            solution_count += len(
                [
                    step_name
                    for step_name in attempt_data.keys()
                    if step_name.startswith("Solution")
                ]
            )

            verification_count += len(
                [
                    step_name
                    for step_name in attempt_data.keys()
                    if step_name.startswith("Verification")
                ]
            )

        execution_metrics["attempts"].append(len(execution_summary))
        execution_metrics["solutions"].append(solution_count)
        execution_metrics["verifications"].append(verification_count)

    return execution_metrics


def plot_execution_profile(figure, execution_metrics: dict[str, list[int]]) -> None:
    """Plot execution complexity and retry metrics.

    Parameters
    ----------
    execution_metrics : dict[str, list[int]]
        Dictionary containing attempts, solutions, and verifications.

    Returns
    -------
    None
    """
    metrics_dataframe = pd.DataFrame(execution_metrics)

    primary_axis = figure.add_subplot(111)

    # PSS: Renamed variables for clarity and improved readability.
    metrics_dataframe[["solutions", "verifications"]].plot(
        kind="bar",
        stacked=True,
        ax=primary_axis,
        color=["#3498db", "#9b59b6"],
        zorder=10,
    )

    max_steps = (
        metrics_dataframe["solutions"] + metrics_dataframe["verifications"]
    ).max()

    primary_axis.set_ylabel("Number of Steps")
    primary_axis.set_yticks(range(1, max_steps + 1))
    primary_axis.grid(True, axis="y", zorder=0)

    secondary_axis = primary_axis.twinx()

    secondary_axis.plot(
        metrics_dataframe.index,
        metrics_dataframe["attempts"],
        color="#e74c3c",
        marker="o",
        linewidth=2,
        label="Global Attempts",
        zorder=10,
    )

    secondary_axis.set_ylabel("Global Attempts")

    max_attempts = metrics_dataframe["attempts"].max() + 1

    secondary_axis.set_yticks(range(1, max_attempts))
    secondary_axis.set_ylim(0, max_attempts)

    primary_axis.set_xticklabels(
        [f"Task {task_index + 1}" for task_index in range(metrics_dataframe.shape[0])]
    )

    plt.title("Execution Profile: Complexity vs Retries")
    # plt.tight_layout()
