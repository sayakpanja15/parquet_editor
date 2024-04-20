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
    """A model to interface a pandas DataFrame with a QTableView."""
    def __init__(self, data=pd.DataFrame()):
        super(PandasModel, self).__init__()
        self._data = data  # The DataFrame to display and manage.

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
            column = self._data.columns[index.column()]
            try:
                validated_value = self.validate_data(column, value)
                self._data.at[index.row(), column] = validated_value
                self.dataChanged.emit(index, index, [Qt.EditRole])
                return True
            except ValueError as e:
                QMessageBox.critical(None, "Validation Error", f"Failed to set data: {str(e)}")
                return False
        return False

    def validate_data(self, column, value):
        """Validate data based on the column data type before setting it."""
        dtype = self._data.dtypes[column]
        if pd.api.types.is_integer_dtype(dtype):
            return int(value)
        elif pd.api.types.is_float_dtype(dtype):
            return float(value)
        elif pd.api.types.is_string_dtype(dtype):
            return str(value)
        else:
            return value  # This defaults to a direct assignment for other types.

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[section])
        return None

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def remove_row(self, position):
        try:
            self.beginRemoveRows(QModelIndex(), position, position)
            self._data.drop(self._data.index[position], axis=0, inplace=True)
            self.endRemoveRows()
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to remove row: {str(e)}")

    def add_column(self, column_name, default_value=None):
        try:
            self._data[column_name] = default_value
            self.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(None, "Column Add Error", f"Failed to add column: {str(e)}")


    def delete_column(self, column_name):
        try:
            if column_name not in self._data.columns:
                QMessageBox.warning(None, "Column Delete Error", "Column not found in the data.")
                return
            self._data.drop(column_name, axis=1, inplace=True)
            self.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(None, "Column Delete Error", f"Failed to delete column: {str(e)}")

    def rename_column(self, old_name, new_name):
        try:
            if old_name not in self._data.columns:
                QMessageBox.warning(None, "Column Rename Error", "Column not found in the data.")
                return
            self._data.rename(columns={old_name: new_name}, inplace=True)
            self.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(None, "Column Rename Error", f"Failed to rename column: {str(e)}")

    def paste_rows(self, position):
        try:
            if not self.clipboard.empty:
                num_rows = len(self.clipboard)
                self.beginInsertRows(QModelIndex(), position, position + num_rows - 1)
                upper_part = self._data.iloc[:position]
                lower_part = self._data.iloc[position:]
                self._data = pd.concat([upper_part, self.clipboard, lower_part]).reset_index(drop=True)
                self.endInsertRows()
        except Exception as e:
            QMessageBox.critical(None, "Paste Error", f"Failed to paste rows: {str(e)}")

    def load_data(self, filename):
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
        try:
            if column not in self._data.columns:
                QMessageBox.warning(None, "Sort Error", "Column not found in the data.")
                return
            # Sorting
            self._data.sort_values(by=column, ascending=ascending, inplace=True)
            # Filtering
            if filter_condition:
                self._data = self._data.query(f"{column} {filter_condition}")
            self.layoutChanged.emit()
        except Exception as e:
            QMessageBox.critical(None, "Sort/Filter Error", f"An error occurred while sorting/filtering: {str(e)}")