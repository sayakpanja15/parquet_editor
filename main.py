import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QTableView, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QPushButton, QVBoxLayout, QWidget, QMenu, QFileDialog, QMessageBox, QCheckBox,
                             QLabel, QHBoxLayout, QStyledItemDelegate, QInputDialog, QAbstractItemView)
from PyQt5.QtCore import QAbstractTableModel, Qt, QThreadPool, QRunnable, QSettings, QItemSelectionModel, QModelIndex

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class Worker(QRunnable):
    """A worker thread for running tasks in the background."""
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute the function assigned to this worker."""
        self.fn(*self.args, **self.kwargs)

class BooleanDelegate(QStyledItemDelegate):
    """A delegate that uses a checkbox for boolean fields in a QTableView."""
    def createEditor(self, parent, option, index):
        """Create a checkbox editor for boolean fields."""
        if isinstance(index.data(), bool):
            editor = QCheckBox(parent)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        """Set editor data from the model."""
        if isinstance(editor, QCheckBox):
            value = index.model().data(index, Qt.EditRole)
            editor.setChecked(value)

    def setModelData(self, editor, model, index):
        """Set model data from the editor."""
        if isinstance(editor, QCheckBox):
            model.setData(index, editor.isChecked(), Qt.EditRole)

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, data=pd.DataFrame()):
        super(PandasModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        """Return the number of rows in the model."""
        return self._data.shape[0]

    def columnCount(self, parent=None):
        """Return the number of columns in the model."""
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        """Return the data at the specified index."""
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._data.iloc[index.row(), index.column()])
        if role == Qt.CheckStateRole and isinstance(self._data.iloc[index.row(), index.column()], bool):
            return Qt.Checked if self._data.iloc[index.row(), index.column()] else Qt.Unchecked
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Set the data at the specified index."""
        if index.isValid() and role == Qt.EditRole:
            dtype = self._data.iloc[index.row(), index.column()].dtype
            try:
                value = dtype.type(value)
                self._data.iloc[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [Qt.EditRole, Qt.DisplayRole])
                return True
            except ValueError:
                return False
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return the header data for the given section and orientation."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def flags(self, index):
        """Return the item flags for the given index."""
        flags = super().flags(index)
        if isinstance(self._data.iloc[index.row(), index.column()], bool):
            flags |= Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        return flags

    def update_data(self, data):
        """Update the model's data."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def insert_column(self, position, column_name, dtype):
        """Insert a new column into the model."""
        if dtype == 'bool':
            default_value = False
        elif 'int' in dtype:
            default_value = 0
        elif 'float' in dtype:
            default_value = 0.0
        else:
            default_value = None
        self.beginInsertColumns(QModelIndex(), position, position)
        self._data.insert(loc=position, column=column_name, value=np.full(self._data.shape[0], default_value, dtype=dtype))
        self.endInsertColumns()

    def remove_column(self, position):
        """Remove a column from the model."""
        self.beginRemoveColumns(QModelIndex(), position, position)
        self._data.drop(self._data.columns[position], axis=1, inplace=True)
        self.endRemoveColumns()

    def remove_row(self, position):
        """Remove a row from the model."""
        self.beginRemoveRows(QModelIndex(), position, position)
        self._data.drop(self._data.index[position], axis=0, inplace=True)
        self.endRemoveRows()

class DataManipulationDialog(QDialog):
    """A dialog for applying data manipulations like pivot tables."""
    def __init__(self, data, parent=None):
        super(DataManipulationDialog, self).__init__(parent)
        self.data = data
        self.initUI()

    def initUI(self):
        """Initialize the UI components of the dialog."""
        self.layout = QVBoxLayout(self)
        self.indexComboBox = QComboBox(self)
        self.indexComboBox.addItems([""] + list(self.data.columns))
        self.columnsComboBox = QComboBox(self)
        self.columnsComboBox.addItems([""] + list(self.data.columns))
        self.valuesComboBox = QComboBox(self)
        self.valuesComboBox.addItems([""] + list(self.data.columns))
        self.functionComboBox = QComboBox(self)
        self.functionComboBox.addItems(["mean", "sum", "count", "max", "min"])
        
        formLayout = QFormLayout()
        formLayout.addRow("Index:", self.indexComboBox)
        formLayout.addRow("Columns:", self.columnsComboBox)
        formLayout.addRow("Values:", self.valuesComboBox)
        formLayout.addRow("Function:", self.functionComboBox)
        self.layout.addLayout(formLayout)

        self.button = QPushButton("Apply", self)
        self.button.clicked.connect(self.apply)
        self.layout.addWidget(self.button)

    def apply(self):
        """Apply the selected data manipulation and update the parent model."""
        if self.indexComboBox.currentText() and self.columnsComboBox.currentText() and self.valuesComboBox.currentText():
            try:
                result = pd.pivot_table(
                    self.data,
                    index=self.indexComboBox.currentText(),
                    columns=self.columnsComboBox.currentText(),
                    values=self.valuesComboBox.currentText(),
                    aggfunc=self.functionComboBox.currentText()
                )
                self.parent().model.update_data(result)
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Operation Error", "Failed to create pivot table: " + str(e))
        else:
            QMessageBox.warning(self, "Input Error", "Please fill all fields.")

class SettingsDialog(QDialog):
    """A dialog for application settings configuration."""
    def __init__(self, settings, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.settings = settings
        self.initUI()

    def initUI(self):
        """Initialize the UI components of the settings dialog."""
        self.layout = QVBoxLayout(self)
        self.defaultPathLineEdit = QLineEdit(self)
        self.defaultPathLineEdit.setText(self.settings.value("defaultPath", ""))
        formLayout = QFormLayout()
        formLayout.addRow("Default Path:", self.defaultPathLineEdit)
        self.layout.addLayout(formLayout)

        self.button = QPushButton("Save", self)
        self.button.clicked.connect(self.save_settings)
        self.layout.addWidget(self.button)

    def save_settings(self):
        """Save the specified settings."""
        self.settings.setValue("defaultPath", self.defaultPathLineEdit.text())
        self.accept()

class App(QMainWindow):
    """The main application window for the DataFrame editor."""
    def __init__(self):
        super(App, self).__init__()
        self.model = PandasModel()
        self.threadpool = QThreadPool()
        self.settings = QSettings('YourCompany', 'DataFrameEditor')
        self.initUI()

    def initUI(self):
        """Initialize the UI components of the main application window."""
        self.restoreSettings()
        self.setWindowTitle("DataFrame Editor")
        self.setGeometry(100, 100, 800, 600)
        self.setCentralWidget(QWidget(self))
        layout = QVBoxLayout(self.centralWidget())
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setItemDelegate(BooleanDelegate())
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.open_menu)
        layout.addWidget(self.table_view)
        self.statusBar = self.statusBar()
        self.setupMenuBar()

    def closeEvent(self, event):
        """Handle the close event to save settings."""
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)

    def restoreSettings(self):
        """Restore saved settings."""
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def load_file(self):
        """Load a file asynchronously."""
        worker = Worker(self.actual_load_file)
        self.threadpool.start(worker)

    def setupMenuBar(self):
        """Setup the menu bar for the application."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        new_action = QAction('&New DataFrame', self)
        new_action.triggered.connect(self.new_dataframe)
        file_menu.addAction(new_action)
        load_action = QAction('&Load File...', self)
        load_action.triggered.connect(self.load_file)
        file_menu.addAction(load_action)
        save_action = QAction('&Save File...', self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        plot_action = QAction('&Plot Data', self)
        plot_action.triggered.connect(self.create_plot)
        file_menu.addAction(plot_action)

        data_menu = menu_bar.addMenu('&Data')
        pivot_action = QAction('&Create Pivot Table', self)
        pivot_action.triggered.connect(self.create_pivot_table)
        data_menu.addAction(pivot_action)

        settings_action = QAction('&Settings', self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)

    def open_menu(self, position):
        """Open a context menu at the specified position in the table view."""
        menu = QMenu()
        add_column_action = QAction('Add Column Here', self)
        add_column_action.triggered.connect(lambda: self.add_column(self.table_view.indexAt(position).column()))
        menu.addAction(add_column_action)

        remove_column_action = QAction('Remove Column Here', self)
        remove_column_action.triggered.connect(lambda: self.remove_column(self.table_view.indexAt(position).column()))
        menu.addAction(remove_column_action)

        remove_row_action = QAction('Remove Row Here', self)
        remove_row_action.triggered.connect(lambda: self.remove_row(self.table_view.indexAt(position).row()))
        menu.addAction(remove_row_action)

        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def new_dataframe(self):
        """Create a new empty DataFrame in the model."""
        self.model.update_data(pd.DataFrame())
        self.statusBar.showMessage("New DataFrame created", 5000)

    def add_column(self, position=None):
        """Add a new column to the DataFrame."""
        column_name, dtype = QInputDialog.getText(self, "Add Column", "Enter column name and data type (e.g., int):").split()
        self.model.insert_column(position if position is not None else len(self.model._data.columns), column_name, dtype)

    def remove_column(self, position):
        """Remove a column from the DataFrame."""
        if position != -1:
            self.model.remove_column(position)
            self.statusBar.showMessage("Column removed", 5000)

    def remove_row(self, position):
        """Remove a row from the DataFrame."""
        if position != -1:
            self.model.remove_row(position)
            self.statusBar.showMessage("Row removed", 5000)

    def actual_load_file(self):
        """Perform the actual file loading operation."""
        options = "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;Parquet Files (*.parquet);;All Files (*)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", options)
        if filename:
            try:
                if filename.endswith('.csv'):
                    data = pd.read_csv(filename)
                elif filename.endswith('.xlsx'):
                    data = pd.read_excel(filename)
                elif filename.endswith('.json'):
                    data = pd.read_json(filename)
                elif filename.endswith('.parquet'):
                    data = pd.read_parquet(filename)
                self.model.update_data(data)
                QMessageBox.information(self, "Success", "File loaded successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", "Failed to load file: " + str(e))

    def create_pivot_table(self):
        """Create a pivot table based on user selections."""
        dialog = DataManipulationDialog(self.model._data, self)
        if dialog.exec_():
            self.statusBar.showMessage("Pivot Table created", 5000)

    def open_settings_dialog(self):
        """Open the settings dialog to adjust application settings."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.statusBar.showMessage("Settings saved", 5000)

    def create_plot(self):
        """Create a plot based on the numerical data in the DataFrame."""
        dialog = PlotDialog(self.model._data, self)
        if dialog.exec_():
            self.statusBar.showMessage("Plot created", 5000)

    def save_file(self):
        """Save the DataFrame to a file."""
        options = "CSV (*.csv);;Excel (*.xlsx);;JSON (*.json);;Parquet (*.parquet)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", "", options)
        if filename:
            try:
                if filename.endswith('.csv'):
                    self.model._data.to_csv(filename)
                elif filename.endswith('.xlsx'):
                    self.model._data.to_excel(filename)
                elif filename.endswith('.json'):
                    self.model._data.to_json(filename)
                elif filename.endswith('.parquet'):
                    self.model._data.to_parquet(filename)
                self.statusBar.showMessage("File saved successfully", 5000)
            except Exception as e:
                self.statusBar.showMessage("Failed to save file: " + str(e), 5000)

class PlotWindow(QMainWindow):
    """A window for displaying plots of the DataFrame's data."""
    def __init__(self, data, plot_type, parent=None):
        super(PlotWindow, self).__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.setCentralWidget(self.canvas)
        ax = self.figure.add_subplot(111)

        if plot_type == 'line':
            for col in data.columns:
                ax.plot(data.index, data[col], label=col)
            ax.legend()
        elif plot_type == 'scatter':
            if len(data.columns) >= 2:
                ax.scatter(data[data.columns[0]], data[data.columns[1]])
                ax.set_xlabel(data.columns[0])
                ax.set_ylabel(data.columns[1])
        else:
            data.hist(ax=ax)

        self.canvas.draw()

class PlotDialog(QDialog):
    """A dialog for choosing the type of plot to generate."""
    def __init__(self, data, parent=None):
        super(PlotDialog, self).__init__(parent)
        self.data = data
        self.initUI()

    def initUI(self):
        """Initialize the UI components of the plot dialog."""
        self.layout = QVBoxLayout(self)
        self.plotTypeComboBox = QComboBox(self)
        self.plotTypeComboBox.addItems(["histogram", "line", "scatter"])
        self.layout.addWidget(self.plotTypeComboBox)

        self.button = QPushButton("Create Plot", self)
        self.button.clicked.connect(self.create_plot)
        self.layout.addWidget(self.button)

    def create_plot(self):
        """Create the selected type of plot."""
        plot_type = self.plotTypeComboBox.currentText()
        numeric_data = self.data.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            if plot_type == 'line' or plot_type == 'scatter':
                if len(numeric_data.columns) < 2:
                    QMessageBox.warning(self, "Plot Error", "Not enough data columns for selected plot type.")
                    return
            self.plot_window = PlotWindow(numeric_data, plot_type)
            self.plot_window.show()
            self.accept()
        else:
            QMessageBox.warning(self, "Plot Error", "No numeric data available to plot.")

def main():
    """The main function to start the PyQt application."""
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
