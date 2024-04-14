import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAction, QTableView, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QPushButton, QVBoxLayout, QWidget, QMenu, QFileDialog, QLabel, QStyledItemDelegate, QCheckBox, QMessageBox, QHBoxLayout)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QAbstractTableModel, Qt, QDate

class BooleanDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.data() in ['True', 'False']:
            editor = QCheckBox(parent)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QCheckBox):
            value = index.model().data(index, Qt.EditRole)
            editor.setChecked(value == 'True')

    def setModelData(self, editor, model, index):
        if isinstance(editor, QCheckBox):
            model.setData(index, 'True' if editor.isChecked() else 'False', Qt.EditRole)

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

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[section]
        return None

    def flags(self, index):
        flags = super().flags(index)
        if self._data.iloc[index.row(), index.column()].dtype == bool:
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

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = PandasModel()
        self.initUI()

    def initUI(self):
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
        self.status_bar = self.statusBar()
        self.setupMenuBar()

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

    def open_menu(self, position):
        menu = QMenu()
        add_column_action = QAction('Add Column Here', self)
        add_column_action.triggered.connect(lambda: self.add_column(self.table_view.indexAt(position).column()))
        menu.addAction(add_column_action)
        menu.exec_(self.table_view.viewport().mapToGlobal(position))

    def new_dataframe(self):
        self.model.update_data(pd.DataFrame())
        self.status_bar.showMessage("New DataFrame created", 5000)

    def add_column(self, position=None):
        dialog = ColumnDialog(self)
        if dialog.exec_():
            column_name, dtype = dialog.get_details()
            self.model.insert_column(position if position is not None else len(self.model._data.columns), column_name, dtype)

    def load_file(self):
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
                self.status_bar.showMessage("File loaded successfully", 5000)
            except Exception as e:
                self.status_bar.showMessage("Failed to load file: " + str(e), 5000)

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
                self.status_bar.showMessage("File saved successfully", 5000)
            except Exception as e:
                self.status_bar.showMessage("Failed to save file: " + str(e), 5000)

def main():
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
# github link: https://github.com/sayakpanja15/parquet_editor