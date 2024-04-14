import sys
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QTableView, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QPushButton, QVBoxLayout, QWidget, QMenu, QFileDialog, QMessageBox, QCheckBox,
                             QLabel, QHBoxLayout, QStyledItemDelegate, QInputDialog)
from PyQt5.QtCore import QAbstractTableModel, Qt, QThreadPool, QRunnable, QSettings, QModelIndex, QItemSelectionModel, QItemSelection
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QPushButton

class Worker(QRunnable):
    """Handle background tasks without freezing the UI."""
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Run the worker function with provided arguments and handle exceptions."""
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Error during background operation: {e}")

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, data=pd.DataFrame()):
        super(PandasModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        """Return the number of rows in the DataFrame."""
        return self._data.shape[0]

    def columnCount(self, parent=None):
        """Return the number of columns in the DataFrame."""
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        """Return the data to be displayed at the given index with the specified role."""
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value) if not pd.isnull(value) else ""
        if role == Qt.CheckStateRole and isinstance(self._data.dtypes[index.column()], (np.bool_, bool)):
            return Qt.Checked if self._data.iloc[index.row(), index.column()] else Qt.Unchecked
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """Set the data at the given index with the specified role to the provided value."""
        if index.isValid() and role in (Qt.EditRole, Qt.CheckStateRole):
            col_type = self._data.dtypes[index.column()]
            try:
                if role == Qt.CheckStateRole:
                    value = bool(value == Qt.Checked)
                else:
                    value = col_type.type(value)
                self._data.iloc[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [role])
                return True
            except ValueError as e:
                QMessageBox.critical(None, "Value Error", f"Failed to convert {value} to {col_type.name}: {e}")
                return False
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return the header data for the given section, orientation, and role."""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None

    def flags(self, index):
        """Return the item flags for the given index."""
        flags = super().flags(index)
        if isinstance(self._data.dtypes[index.column()], (np.bool_, bool)):
            flags |= Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        else:
            flags |= Qt.ItemIsEditable
        return flags

    def update_data(self, data):
        """Update the model with a new DataFrame."""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def insert_column(self, position, column_name, dtype):
        """Insert a new column at the given position with the specified name and data type."""
        if dtype not in ['bool', 'int32', 'float', 'object']:
            QMessageBox.warning(None, "Data Type Error", "Invalid data type specified.")
            return

        default_value = False if dtype == 'bool' else 0 if 'int' in dtype else 0.0 if 'float' in dtype else ""
        self.beginInsertColumns(QModelIndex(), position, position)
        self._data.insert(loc=position, column=column_name, value=np.full(self._data.shape[0], default_value, dtype=dtype))
        self.endInsertColumns()

    def remove_column(self, position):
        """Remove the column at the given position."""
        self.beginRemoveColumns(QModelIndex(), position, position)
        self._data.drop(self._data.columns[position], axis=1, inplace=True)
        self.endRemoveColumns()

    def remove_row(self, position):
        """Remove the row at the given position."""
        self.beginRemoveRows(QModelIndex(), position, position)
        self._data.drop(self._data.index[position], axis=0, inplace=True)
        self.endRemoveRows()



class SettingsDialog(QDialog):
    """A dialog for application settings configuration."""
    def __init__(self, settings, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.settings = settings
        self.initUI()

    def initUI(self):
        """Initialize the UI components of the settings dialog."""
        self.setWindowTitle("Settings")
        self.setGeometry(300, 300, 400, 200)
        layout = QVBoxLayout(self)

        # Create form layout for input fields
        formLayout = QFormLayout()

        # Default path setting
        self.defaultPathLineEdit = QLineEdit(self)
        self.defaultPathLineEdit.setText(self.settings.value("defaultPath", ""))
        formLayout.addRow(QLabel("Default Path:"), self.defaultPathLineEdit)

        # Add form layout to main layout
        layout.addLayout(formLayout)

        # Save button
        self.buttonSave = QPushButton("Save", self)
        self.buttonSave.clicked.connect(self.save_settings)
        layout.addWidget(self.buttonSave)

    def save_settings(self):
        """Save the specified settings."""
        self.settings.setValue("defaultPath", self.defaultPathLineEdit.text().strip())
        self.accept()  # Close the dialog

        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")


class App(QMainWindow):
    """The main application window for the DataFrame editor."""
    def __init__(self):
        super(App, self).__init__()
        self.model = PandasModel()
        self.threadpool = QThreadPool()
        self.settings = QSettings('YourCompany', 'DataFrameEditor')
        self.initUI()

    def initUI(self):
        """Initialize the user interface."""
        self.restoreSettings()
        self.setWindowTitle("DataFrame Editor")
        self.setGeometry(100, 100, 800, 600)
        self.setCentralWidget(QWidget(self))
        layout = QVBoxLayout(self.centralWidget())
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.open_menu)
        layout.addWidget(self.table_view)
        self.statusBar = self.statusBar()
        self.setupMenuBar()

    def closeEvent(self, event):
        """Save the window geometry when the application is closed."""
        self.settings.setValue('geometry', self.saveGeometry())
        super().closeEvent(event)

    def restoreSettings(self):
        """Restore the window geometry from the settings."""
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

    def setupMenuBar(self):
        """Create the main menu bar with actions for file operations."""
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
        settings_action = QAction('&Settings', self)
        settings_action.triggered.connect(self.open_settings_dialog)
        file_menu.addAction(settings_action)

    def open_menu(self, position):
        """Open a context menu at the given position."""
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
        """Create a new empty DataFrame."""
        self.model.update_data(pd.DataFrame())
        self.statusBar.showMessage("New DataFrame created", 5000)

    def add_column(self, position=None):
        """Prompt the user to add a new column to the DataFrame."""
        text, ok = QInputDialog.getText(self, "Add Column", "Enter column name and data type (e.g., int):")
        if ok and text:
            try:
                column_name, dtype = text.split()
                self.model.insert_column(position if position is not None else len(self.model._data.columns), column_name, dtype)
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter a column name followed by a data type.")

    def remove_column(self, position):
        """Remove the column at the given position."""
        if position != -1:
            self.model.remove_column(position)
            self.statusBar.showMessage("Column removed", 5000)

    def remove_row(self, position):
        """Remove the row at the given position."""
        if position != -1:
            self.model.remove_row(position)
            self.statusBar.showMessage("Row removed", 5000)

    def load_file(self):
        """Prompt the user to select a file to load into the DataFrame."""
        worker = Worker(self.actual_load_file)
        self.threadpool.start(worker)

    def actual_load_file(self):
        """Load a file into the DataFrame."""
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

    def save_file(self):
        """Prompt the user to select a file to save the DataFrame."""
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
                QMessageBox.critical(self, "Error", "Failed to save file: " + str(e))

    def open_settings_dialog(self):
        """Open the settings dialog to allow the user to configure application settings."""
        settings_dialog = SettingsDialog(self.settings, self)
        if settings_dialog.exec_():
            self.statusBar.showMessage("Settings saved", 5000)

def main():
    """Create the main application window."""
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
