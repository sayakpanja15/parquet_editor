# data_visualization.py
import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QComboBox, QLabel, QWidget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class PlotDialog(QDialog):
    """
    A dialog that provides options for plotting selected data from a pandas DataFrame.
    """

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Data Visualization")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout(self)

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Line Plot", "Histogram", "Scatter Plot"])
        layout.addWidget(QLabel("Select plot type:"))
        layout.addWidget(self.plot_type_combo)

        self.column_select_combo = QComboBox()
        self.column_select_combo.addItems(self.data.columns.tolist())
        layout.addWidget(QLabel("Select column:"))
        layout.addWidget(self.column_select_combo)

        plot_button = QPushButton("Plot")
        plot_button.clicked.connect(self.plot_data)
        layout.addWidget(plot_button)

        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        layout.addWidget(self.canvas)

    def plot_data(self):
        plot_type = self.plot_type_combo.currentText()
        column = self.column_select_combo.currentText()
        ax = self.canvas.figure.subplots()
        ax.clear()

        if plot_type == "Line Plot":
            self.data[column].plot(ax=ax, kind='line')
        elif plot_type == "Histogram":
            self.data[column].plot(ax=ax, kind='hist', bins=30)
        elif plot_type == "Scatter Plot":
            if self.data.shape[1] < 2:
                self.showError("Scatter plot requires at least two columns")
                return
            y_column = self.choose_y_column(column)
            self.data.plot(ax=ax, kind='scatter', x=column, y=y_column)

        self.canvas.draw()

    def choose_y_column(self, x_column):
        """Utility function to choose a y column for scatter plots, excluding the x_column."""
        cols = self.data.columns.tolist()
        cols.remove(x_column)
        return cols[0]  # Return the first column not being used as the x-axis

    def showError(self, message):
        QMessageBox.critical(self, "Error", message)
