# main_app.py
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMdiArea, QMdiSubWindow, QFileDialog,
    QMessageBox, QLabel, QToolBar, QTableView, QWidget, QDialog, QVBoxLayout, QComboBox,
    QLineEdit, QRadioButton, QPushButton, QHBoxLayout
)
from data_visualisation import PlotDialog
from pandas_model import PandasModel
from gui_and_visuals import DockablePanels, ThemeSupport
from data_exploration import DataExploration
from PyQt5.QtCore import Qt

class SortFilterDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sort and Filter")
        self.setGeometry(100, 100, 300, 200)
        layout = QVBoxLayout(self)
        self.column_select = QComboBox()
        self.column_select.addItems(self.columns)
        self.asc_radio = QRadioButton("Ascending")
        self.asc_radio.setChecked(True)
        self.desc_radio = QRadioButton("Descending")
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(self.asc_radio)
        sort_layout.addWidget(self.desc_radio)
        self.filter_condition = QLineEdit()
        self.filter_condition.setPlaceholderText("Enter filter condition (e.g., > 10)")
        self.apply_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Cancel")
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        layout.addWidget(QLabel("Select Column:"))
        layout.addWidget(self.column_select)
        layout.addWidget(QLabel("Sort Order:"))
        layout.addLayout(sort_layout)
        layout.addWidget(QLabel("Filter Condition:"))
        layout.addWidget(self.filter_condition)
        layout.addLayout(button_layout)
        self.apply_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)

    def apply(self):
        column = self.column_select.currentText()
        ascending = self.asc_radio.isChecked()
        filter_cond = self.filter_condition.text()
        self.accept()
        self.parent().apply_sort_filter(column, ascending, filter_cond)

class App(QWidget):
    def __init__(self):
        super(App, self).__init__()
        self.model = PandasModel()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)
        layout.addWidget(self.table_view)
        self.statusBar = QLabel("Ready")
        layout.addWidget(self.statusBar)
        self.table_view.selectionModel().selectionChanged.connect(self.update_status_bar)

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
        self.dockable_panels = DockablePanels(self)  # Initialize Dockable Panels
        self.theme_support = ThemeSupport(self)  # Initialize Theme Support
        self.setupMenuBar()
        self.setupToolbar()
        self.dockable_panels.add_quick_stats_panel()
        self.data_exploration_panel = DataExploration(self)
        self.dockable_panels.create_dockable_panel("Data Exploration", Qt.RightDockWidgetArea,
                                                   self.data_exploration_panel)

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

        sort_filter_action = QAction('Sort/Filter', self)
        sort_filter_action.triggered.connect(self.open_sort_filter_dialog)
        file_menu.addAction(sort_filter_action)

        plot_action = QAction('Plot Data', self)  # Action for opening the plot dialog
        plot_action.triggered.connect(self.open_plot_dialog)
        file_menu.addAction(plot_action)

    def open_plot_dialog(self):
        sub_window = self.active_subwindow()
        if sub_window:
            data = sub_window.widget().model._data  # Assuming the data is stored here
            dialog = PlotDialog(data)
            dialog.exec_()

    def open_sort_filter_dialog(self):
        sub_window = self.active_subwindow()
        if sub_window:
            columns = sub_window.widget().model._data.columns.tolist()
            dialog = SortFilterDialog(columns, sub_window.widget())
            dialog.exec_()

    def apply_sort_filter(self, column, ascending, filter_cond):
        sub_window = self.active_subwindow()
        if sub_window:
            sub_window.widget().model.sort_and_filter(column, ascending, filter_cond)

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
            filename, _ = QFileDialog.getOpenFileName(self, "Open File", "",
                                                      "All Files (*);;CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;Parquet Files (*.parquet)")
            if filename:
                sub_window.widget().model.load_data(filename)
                # After loading data, update data exploration panel
                dataframe = sub_window.widget().model._data
                self.data_exploration_panel.update_stats(dataframe)
                self.data_exploration_panel.update_summaries(dataframe)
        else:
            QMessageBox.warning(self, "No Active Window", "There is no active DataFrame window open.")

    def save(self):
        sub_window = self.active_subwindow()
        if sub_window:
            filename, _ = QFileDialog.getSaveFileName(self, "Save File", "",
                                                      "CSV Files (*.csv);;Excel Files (*.xlsx);;JSON Files (*.json);;Parquet Files (*.parquet)")
            if filename:
                sub_window.widget().model.save_data(filename)
        else:
            QMessageBox.warning(self, "No Active Window", "There is no active DataFrame window open.")

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


def main():
    app = QApplication(sys.argv)
    main_app = MainApp()
    main_app.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
