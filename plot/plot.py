import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


class Plot:
    """
    Generic plotting class that takes a pandas DataFrame and plots
    multiple y-axis lines with an optional bar chart at the bottom.
    """

    def __init__(self, df):
        """
        Initialize the Plot class with a pandas DataFrame.

        Args:
            df (pandas.DataFrame): The source data.
        """
        self.df = df.copy()

    def plot(self, x, y_lines, bar_column=None, figsize=(14, 8), title="Chart"):
        """
        Plot one or more line series, each with its own y-axis scale,
        sharing the x-axis, with an optional bar series at the bottom.

        Args:
            x (str): Column name to use for the x-axis.
            y_lines (list[str]): List of column names to plot as lines.
            bar_column (str | None): Column name to plot as bars at the bottom.
                If None, only lines are plotted.
            figsize (tuple): Figure size (width, height).
            title (str): Plot title.

        Returns:
            tuple: (fig, axes) – the matplotlib Figure and a tuple of Axes.
        """
        has_bars = bar_column is not None

        if has_bars:
            fig, (ax_lines, ax_bars) = plt.subplots(
                2, 1, figsize=figsize, height_ratios=[3, 1],
                sharex=True, gridspec_kw={'hspace': 0.05},
            )
        else:
            fig, ax_lines = plt.subplots(1, 1, figsize=figsize)
            ax_bars = None

        # --- line plots, each on its own y-axis ---
        colors = plt.cm.tab10.colors
        axes_list = []

        for idx, col in enumerate(y_lines):
            color = colors[idx % len(colors)]

            if idx == 0:
                ax = ax_lines
            else:
                ax = ax_lines.twinx()
                # Offset additional spines so they don't overlap
                if idx > 1:
                    ax.spines['right'].set_position(('axes', 1 + (idx - 1) * 0.12))

            ax.plot(
                self.df[x], self.df[col],
                linewidth=1, alpha=0.85, color=color, label=col,
            )
            ax.set_ylabel(col, fontsize=11, color=color)
            ax.tick_params(axis='y', labelcolor=color, labelsize=10)
            axes_list.append(ax)

        ax_lines.set_title(title, fontsize=14, fontweight='bold')
        ax_lines.grid(True, alpha=0.3)

        # Combine legends from all twin axes
        lines = []
        labels = []
        for ax in axes_list:
            ln, lb = ax.get_legend_handles_labels()
            lines.extend(ln)
            labels.extend(lb)
        ax_lines.legend(lines, labels, loc='upper right', fontsize=9)

        # --- bar chart ---
        if has_bars and ax_bars is not None:
            # Calculate bar width from actual data spacing
            if len(self.df[x]) > 1:
                diffs = self.df[x].diff().dropna()
                median_diff = diffs.median()
                if isinstance(median_diff, pd.Timedelta):
                    bar_width = median_diff * 0.8
                else:
                    bar_width = float(median_diff) * 0.8
            else:
                bar_width = 0.8

            ax_bars.bar(
                self.df[x], self.df[bar_column], width=bar_width,
                color='steelblue', alpha=0.7, edgecolor='darkblue', linewidth=0.5,
            )
            ax_bars.set_ylabel(bar_column.capitalize(), fontsize=11)
            ax_bars.set_xlabel(x.capitalize(), fontsize=11)
            ax_bars.grid(True, alpha=0.3)
            ax_bars.tick_params(axis='both', labelsize=10)
        else:
            ax_lines.set_xlabel(x.capitalize(), fontsize=11)

        # --- x-axis date formatting (if datetime) ---
        bottom_ax = ax_bars if has_bars else ax_lines
        if pd.api.types.is_datetime64_any_dtype(self.df[x]):
            bottom_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            bottom_ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(bottom_ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        axes = (ax_lines, ax_bars) if has_bars else (ax_lines,)
        return fig, axes

    def show(self, x, y_lines, bar_column=None, figsize=(14, 8), title="Chart"):
        """
        Convenience method: plot and display immediately.

        Args:
            x (str): Column name for the x-axis.
            y_lines (list[str]): Column names to plot as lines.
            bar_column (str | None): Column name to plot as bars at the bottom.
            figsize (tuple): Figure size.
            title (str): Plot title.
        """
        self.plot(x, y_lines, bar_column=bar_column, figsize=figsize, title=title)
        plt.show()
