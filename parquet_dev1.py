import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QTableView, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QPushButton, QVBoxLayout, QWidget, QMenu, QFileDialog, QMessageBox, QCheckBox,
                             QLabel, QHBoxLayout, QStyledItemDelegate, QAbstractItemView)
from PyQt5.QtCore import QAbstractTableModel, Qt, QThreadPool, QRunnable, QSettings, QItemSelectionModel, QModelIndex

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.fn(*self.args, **self.kwargs)

class BooleanDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if isinstance(index.data(), bool):
            editor = QCheckBox(parent)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QCheckBox):
            value = index.model().data(index, Qt.EditRole)
            editor.setChecked(value)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QCheckBox):
            model.setData(index, editor.isChecked(), Qt.EditRole)

class PandasModel(QAbstractTableModel):
    def __init__(self, data=pd.DataFrame()):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
            if role == Qt.CheckStateRole and isinstance(self._data.iloc[index.row(), index.column()], bool):
                return Qt.Checked if self._data.iloc[index.row(), index.column()] else Qt.Unchecked
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [Qt.EditRole])
            return True
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[section]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def flags(self, index):
        flags = super().flags(index)
        if isinstance(self._data.iloc[index.row(), index.column()], bool):
            flags |= Qt.ItemIsUserCheckable
        flags |= Qt.ItemIsEditable
        return flags

    def update_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def insert_column(self, position, column_name, dtype):
        self.beginResetModel()
        self._data.insert(loc=position, column=column_name, value=pd.Series(dtype=np.dtype(dtype)))
        self.endResetModel()

class DataManipulationDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        # Add controls to configure the pivot table or grouping
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
        if self.indexComboBox.currentText() and self.columnsComboBox.currentText() and self.valuesComboBox.currentText():
            result = pd.pivot_table(
                self.data,
                index=self.indexComboBox.currentText(),
                columns=self.columnsComboBox.currentText(),
                values=self.valuesComboBox.currentText(),
                aggfunc=self.functionComboBox.currentText()
            )
            self.parent().model.update_data(result)
            self.accept()
        else:
            QMessageBox.warning(self, "Input Error", "Please fill all fields.")

class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        # Create layout and widgets for settings
        self.defaultPathLineEdit = QLineEdit(self)
        self.defaultPathLineEdit.setText(self.settings.value("defaultPath", ""))
        formLayout = QFormLayout()
        formLayout.addRow("Default Path:", self.defaultPathLineEdit)
        self.layout.addLayout(formLayout)

        self.button = QPushButton("Save", self)
        self.button.clicked.connect(self.save_settings)
        self.layout.addWidget(self.button)

    def save_settings(self):
        self.settings.setValue("defaultPath", self.defaultPathLineEdit.text())
        self.accept()

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = PandasModel()
        self.threadpool = QThreadPool()
        self.settings = QSettings('YourCompany', 'ParquetEditor')
        self.initUI()

    def initUI(self):
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
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)

    def restoreSettings(self):
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def load_file(self):
        worker = Worker(self.actual_load_file)
        self.threadpool.start(worker)

    def setupMenuBar(self):
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
        menu = QMenu()
        add_column_action = QAction('Add Column Here', self)
        add_column_action.triggered.connect(lambda: self.add_column(self.table_view.indexAt(position).column()))
        menu.addAction(add_column_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def new_dataframe(self):
        self.model.update_data(pd.DataFrame())
        self.statusBar.showMessage("New DataFrame created", 5000)

    def add_column(self, position=None):
        dialog = ColumnDialog(self)
        if dialog.exec_():
            column_name, dtype = dialog.get_details()
            self.model.insert_column(position if position is not None else len(self.model._data.columns), column_name, dtype)

    def actual_load_file(self):
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
        dialog = DataManipulationDialog(self.model._data, self)
        if dialog.exec_():
            self.statusBar.showMessage("Pivot Table created", 5000)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.statusBar.showMessage("Settings saved", 5000)

    def create_plot(self):
        data = self.model._data.select_dtypes(include=[np.number])
        if not data.empty:
            self.plot_window = PlotWindow(data)
            self.plot_window.show()
        else:
            QMessageBox.warning(self, "Plot Error", "No numeric data available to plot.")

    def save_file(self):
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
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.setCentralWidget(self.canvas)
        ax = self.figure.add_subplot(111)
        data.hist(ax=ax)
        self.canvas.draw()

def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
