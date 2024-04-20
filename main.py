import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMdiArea, QMdiSubWindow, QFileDialog,
    QVBoxLayout, QWidget, QTableView, QLabel, QToolBar, QActionGroup, QMessageBox,
)

from PyQt5 import QtGui
from PyQt5.QtGui import QIcon

import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex

class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, data=pd.DataFrame()):
        super(PandasModel, self).__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value) if not pd.isnull(value) else ""
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        return None

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def remove_row(self, position):
        self.beginRemoveRows(QModelIndex(), position, position)
        self._data.drop(self._data.index[position], axis=0, inplace=True)
        self.endRemoveRows()

    def cut_rows(self, rows):
        self.clipboard = self._data.iloc[rows].copy()
        self._data.drop(self._data.index[rows], inplace=True)
        self.layoutChanged.emit()

    def paste_rows(self, position):
        if self.clipboard is not None and not self.clipboard.empty:
            num_rows = len(self.clipboard)
            self.beginInsertRows(QModelIndex(), position, position + num_rows - 1)
            upper_part = self._data.iloc[:position]
            lower_part = self._data.iloc[position:]
            self._data = pd.concat([upper_part, self.clipboard, lower_part]).reset_index(drop=True)
            self.endInsertRows()

    def load_data(self, filename):
        if filename.endswith('.csv'):
            self._data = pd.read_csv(filename)
        elif filename.endswith('.xlsx'):
            self._data = pd.read_excel(filename)
        elif filename.endswith('.json'):
            self._data = pd.read_json(filename)
        elif filename.endswith('.parquet'):
            self._data = pd.read_parquet(filename)
        self.layoutChanged.emit()

    def save_data(self, filename):
        if filename.endswith('.csv'):
            self._data.to_csv(filename)
        elif filename.endswith('.xlsx'):
            self._data.to_excel(filename)
        elif filename.endswith('.json'):
            self._data.to_json(filename)
        elif filename.endswith('.parquet'):
            self._data.to_parquet(filename)


class App(QWidget):
    def __init__(self):
        super(App, self).__init__()
        self.model = PandasModel()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)  # Allow selecting multiple cells
        layout.addWidget(self.table_view)

        self.statusBar = QLabel()
        layout.addWidget(self.statusBar)
        self.table_view.selectionModel().selectionChanged.connect(self.update_status_bar)

    def cut(self):
        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if selected_indexes:
            rows = sorted(set(index.row() for index in selected_indexes))
            self.model.cut_rows(rows)
            self.statusBar.setText("Cells cut")
        else:
            self.statusBar.setText("No cells selected")

    def update_status_bar(self):
        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if selected_indexes:
            rows = sorted(set(index.row() for index in selected_indexes))
            columns = sorted(set(index.column() for index in selected_indexes))
            self.statusBar.setText(f"Selected Cells: {len(selected_indexes)} - Rows: {rows} - Columns: {columns}")
        else:
            self.statusBar.setText("No cells selected")


class MainApp(QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)
        self.setWindowTitle('Main Application Window')
        self.setGeometry(100, 100, 1200, 800)
        self.setupMenuBar()
        self.setupToolbar()
        self.open_new_subwindow()  # Open an empty subwindow on startup

    def setupMenuBar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')

        new_window_action = QAction('&New DataFrame Window', self)
        new_window_action.triggered.connect(self.open_new_subwindow)
        file_menu.addAction(new_window_action)

        load_action = QAction(QIcon.fromTheme("document-open"), 'Load', self)
        load_action.triggered.connect(self.load)
        file_menu.addAction(load_action)

        save_action = QAction(QIcon.fromTheme("document-save"), 'Save', self)
        save_action.triggered.connect(self.save)
        file_menu.addAction(save_action)

    def setupToolbar(self):
        toolbar = QToolBar("Editor Toolbar")
        self.addToolBar(toolbar)

        cut_action = QAction(QIcon.fromTheme("edit-cut"), 'Cut', self)
        cut_action.triggered.connect(self.cut)
        toolbar.addAction(cut_action)

        paste_action = QAction(QIcon.fromTheme("edit-paste"), 'Paste', self)
        paste_action.triggered.connect(self.paste)
        toolbar.addAction(paste_action)

        delete_action = QAction(QIcon.fromTheme("edit-delete"), 'Delete', self)
        delete_action.triggered.connect(self.delete)
        toolbar.addAction(delete_action)

    def cut(self):
        sub_window = self.active_subwindow()
        if sub_window:
            sub_window.widget().cut()

    def paste(self):
        sub_window = self.active_subwindow()
        if sub_window:
            sub_window.widget().paste()

    def delete(self):
        sub_window = self.active_subwindow()
        if sub_window:
            sub_window.widget().delete()

    def active_subwindow(self):
        return self.mdi_area.currentSubWindow()

    def open_new_subwindow(self):
        sub_window = QMdiSubWindow()
        app = App()
        sub_window.setWidget(app)
        sub_window.setWindowTitle("DataFrame Editor")
        self.mdi_area.addSubWindow(sub_window)
        sub_window.show()

    def load(self):
        sub_window = self.active_subwindow()
        if sub_window:
            filename, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;Parquet Files (*.parquet)")
            if filename:
                sub_window.widget().model.load_data(filename)
        else:
            QMessageBox.warning(self, "No Active Window", "There is no active DataFrame window open.")

    def save(self):
        sub_window = self.active_subwindow()
        if sub_window:
            filename, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;Parquet Files (*.parquet)")
            if filename:
                sub_window.widget().model.save_data(filename)
        else:
            QMessageBox.warning(self, "No Active Window", "There is no active DataFrame window open.")


def main():
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
