import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplcursors
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

    def _create_subplots(self, n_lines, has_bars, figsize):
        """Create figure and subplots with appropriate height ratios."""
        n_rows = n_lines + (1 if has_bars else 0)
        height_ratios = [2] * n_lines + ([1] if has_bars else [])

        fig, axes = plt.subplots(
            n_rows, 1, figsize=figsize, sharex=True,
            height_ratios=height_ratios,
            gridspec_kw={'hspace': 0.08},
        )

        if n_rows == 1:
            axes = [axes]

        return fig, axes

    def _plot_line(self, ax, x, col, color):
        """Plot a single line series on the given axes."""
        ax.plot(
            self.df[x], self.df[col],
            linewidth=1, alpha=0.85, color=color, label=col,
        )
        ax.set_ylabel(col, fontsize=11, color=color)
        ax.tick_params(axis='y', labelcolor=color, labelsize=10)
        ax.yaxis.set_label_position('left')
        ax.yaxis.tick_left()
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)

    def _plot_bars(self, ax, x, bar_column):
        """Plot a bar chart on the given axes with auto-calculated width."""
        if len(self.df[x]) > 1:
            diffs = self.df[x].diff().dropna()
            median_diff = diffs.median()
            if isinstance(median_diff, pd.Timedelta):
                bar_width = median_diff * 0.8
            else:
                bar_width = float(median_diff) * 0.8
        else:
            bar_width = 0.8

        ax.bar(
            self.df[x], self.df[bar_column], width=bar_width,
            color='steelblue', alpha=0.7, edgecolor='darkblue', linewidth=0.5,
        )
        ax.set_ylabel(bar_column.capitalize(), fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='both', labelsize=10)

    def _format_x_axis(self, ax, x):
        """Apply x-axis label and datetime formatting if applicable."""
        ax.set_xlabel(x.capitalize(), fontsize=11)

        if pd.api.types.is_datetime64_any_dtype(self.df[x]):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    def _add_hover_cursors(self, axes, x):
        """Attach interactive hover tooltips to all line artists."""
        is_datetime = pd.api.types.is_datetime64_any_dtype(self.df[x])

        for ax in axes:
            for artist in ax.get_children():
                if isinstance(artist, plt.Line2D) and len(artist.get_xdata()) > 0:
                    cursor = mplcursors.cursor(artist, hover=True)

                    @cursor.connect("add")
                    def on_add(sel, _is_dt=is_datetime):
                        xi, yi = sel.target
                        if _is_dt:
                            x_label = mdates.num2date(xi).strftime('%H:%M:%S')
                        else:
                            x_label = f"{xi:.4f}"
                        sel.annotation.set_text(f"x={x_label}\ny={yi:.6f}")

    def plot(self, x, y_lines, bar_column=None, figsize=(14, 8), title="Chart"):
        """
        Plot one or more line series, each in its own subplot with its own
        y-axis scale on the left, all sharing the x-axis. An optional bar
        series is rendered at the bottom.

        Args:
            x (str): Column name to use for the x-axis.
            y_lines (list[str]): List of column names to plot as lines.
            bar_column (str | None): Column name to plot as bars at the bottom.
                If None, only lines are plotted.
            figsize (tuple): Figure size (width, height).
            title (str): Plot title.

        Returns:
            tuple: (fig, axes) – the matplotlib Figure and a list of Axes.
        """
        has_bars = bar_column is not None
        fig, axes = self._create_subplots(len(y_lines), has_bars, figsize)

        colors = plt.cm.tab10.colors
        for idx, col in enumerate(y_lines):
            self._plot_line(axes[idx], x, col, colors[idx % len(colors)])

        axes[0].set_title(title, fontsize=14, fontweight='bold')

        if has_bars:
            self._plot_bars(axes[-1], x, bar_column)

        self._format_x_axis(axes[-1], x)
        plt.tight_layout()
        self._add_hover_cursors(axes, x)

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
