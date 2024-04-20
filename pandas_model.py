# pandas_model.py
import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtWidgets import QDialog, QComboBox, QLineEdit, QRadioButton, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QMessageBox


class SortFilterDialog(QDialog):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sort and Filter")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout(self)

        # Column selection
        self.column_select = QComboBox()
        self.column_select.addItems(self.columns)

        # Sort options
        self.asc_radio = QRadioButton("Ascending")
        self.asc_radio.setChecked(True)
        self.desc_radio = QRadioButton("Descending")

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(self.asc_radio)
        sort_layout.addWidget(self.desc_radio)

        # Filter condition
        self.filter_condition = QLineEdit()
        self.filter_condition.setPlaceholderText("Enter filter condition (e.g., > 10)")

        # Buttons
        self.apply_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Cancel")
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)

        # Layout setup
        layout.addWidget(QLabel("Select Column:"))
        layout.addWidget(self.column_select)
        layout.addWidget(QLabel("Sort Order:"))
        layout.addLayout(sort_layout)
        layout.addWidget(QLabel("Filter Condition:"))
        layout.addWidget(self.filter_condition)
        layout.addLayout(button_layout)

        # Connections
        self.apply_button.clicked.connect(self.apply)
        self.cancel_button.clicked.connect(self.reject)

    def apply(self):
        column = self.column_select.currentText()
        ascending = self.asc_radio.isChecked()
        filter_cond = self.filter_condition.text()
        self.accept()  # Close the dialog
        self.parent().apply_sort_filter(column, ascending, filter_cond)


class PandasModel(QAbstractTableModel):
    """A model to interface a pandas DataFrame with a QTableView.

    Attributes:
        _data (pd.DataFrame): The DataFrame to display and manage.
        clipboard (pd.DataFrame): Temporary storage for cut or copied rows.
    """
    def __init__(self, data=pd.DataFrame()):
        super(PandasModel, self).__init__()
        self._data = data
        self.clipboard = pd.DataFrame()

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            value = self._data.iloc[index.row(), index.column()]
            return str(value) if not pd.isnull(value) else ""
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            try:
                self._data.iloc[index.row(), index.column()] = self.validate_data(index.column(), value)
                self.dataChanged.emit(index, index, [Qt.EditRole])
                return True
            except ValueError:
                return False
        return False

    def validate_data(self, column, value):
        """Validate data based on column type before setting it."""
        if column == 0:  # Example: Column 0 expects integer values
            return int(value)
        return value  # Default: accept the value as is

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        return None

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def remove_row(self, position):
        """Remove a row from the model."""
        self.beginRemoveRows(QModelIndex(), position, position)
        self._data.drop(self._data.index[position], axis=0, inplace=True)
        self.endRemoveRows()

    def cut_rows(self, rows):
        """Cut specified rows and store them in the clipboard."""
        self.clipboard = self._data.iloc[rows].copy()
        self._data.drop(self._data.index[rows], inplace=True)
        self.layoutChanged.emit()

    def copy_rows(self, rows):
        """Copy specified rows to the clipboard."""
        self.clipboard = self._data.iloc[rows].copy()

    def add_column(self, column_name, default_value=None):
        self._data[column_name] = default_value
        self.layoutChanged.emit()

    def delete_column(self, column_name):
        self._data.drop(column_name, axis=1, inplace=True)
        self.layoutChanged.emit()

    def rename_column(self, old_name, new_name):
        self._data.rename(columns={old_name: new_name}, inplace=True)
        self.layoutChanged.emit()

    def duplicate_rows(self, rows):
        duplicates = self._data.iloc[rows].copy()
        self._data = pd.concat([self._data, duplicates], ignore_index=True)
        self.layoutChanged.emit()

    def paste_rows(self, position):
        """Paste clipboard rows into the specified position in the DataFrame."""
        if not self.clipboard.empty:
            num_rows = len(self.clipboard)
            self.beginInsertRows(QModelIndex(), position, position + num_rows - 1)
            upper_part = self._data.iloc[:position]
            lower_part = self._data.iloc[position:]
            self._data = pd.concat([upper_part, self.clipboard, lower_part]).reset_index(drop=True)
            self.endInsertRows()

    def load_data(self, filename):
        """Load data from a file into the DataFrame."""
        try:
            if filename.endswith('.csv'):
                self._data = pd.read_csv(filename)
            elif filename.endswith('.xlsx'):
                self._data = pd.read_excel(filename)
            elif filename.endswith('.json'):
                self._data = pd.read_json(filename)
            elif filename.endswith('.parquet'):
                self._data = pd.read_parquet(filename)
            self.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(None, "File Load Error", f"An error occurred while loading the file: {str(e)}")


    def save_data(self, filename):
        """Save the DataFrame data to a file."""
        try:
            if filename.endswith('.csv'):
                self._data.to_csv(filename)
            elif filename.endswith('.xlsx'):
                self._data.to_excel(filename)
            elif filename.endswith('.json'):
                self._data.to_json(filename, orient='records', lines=True)
            elif filename.endswith('.parquet'):
                self._data.to_parquet(filename)
        except Exception as e:
            QMessageBox.critical(None, "File Save Error", f"An error occurred while saving the file: {str(e)}")

    def sort_and_filter(self, column, ascending=True, filter_condition=None):
        # Sorting
        self._data.sort_values(by=column, ascending=ascending, inplace=True)

        # Filtering
        if filter_condition:
            try:
                self._data = self._data.query(f"{column}{filter_condition}")
            except Exception as e:
                QMessageBox.critical(None, "Filter Error", f"An error occurred while filtering: {str(e)}")

        self.layoutChanged.emit()

