from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit, QMessageBox, QComboBox
import pandas as pd

class DataExploration(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = pd.DataFrame()  # Initialize an empty DataFrame
        self.layout = QVBoxLayout(self)
        self.init_ui()

    def init_ui(self):
        # Column Selector
        self.column_selector = QComboBox()
        self.column_selector.currentIndexChanged.connect(self.update_selected_column)
        self.selected_column = None

        # Quick Stats Panel
        self.stats_label = QLabel("Quick Statistics for Selected Column:")
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)

        # Column Summaries
        self.summaries_label = QLabel("Column Summaries:")
        self.summaries_text = QTextEdit()
        self.summaries_text.setReadOnly(True)

        # Custom Query Editor
        self.query_label = QLabel("Custom Query Editor:")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter your SQL-like query here...")
        self.query_button = QPushButton("Execute Query")
        self.query_button.clicked.connect(self.execute_query)

        # Scripting Panel
        self.script_label = QLabel("Python Scripting:")
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("Write your Python script here...")
        self.script_button = QPushButton("Run Script")
        self.script_button.clicked.connect(self.run_script)

        # Layout configuration
        self.layout.addWidget(self.column_selector)
        self.layout.addWidget(self.stats_label)
        self.layout.addWidget(self.stats_text)
        self.layout.addWidget(self.summaries_label)
        self.layout.addWidget(self.summaries_text)
        self.layout.addWidget(self.query_label)
        self.layout.addWidget(self.query_input)
        self.layout.addWidget(self.query_button)
        self.layout.addWidget(self.script_label)
        self.layout.addWidget(self.script_input)
        self.layout.addWidget(self.script_button)

    def execute_query(self):
        """Execute the custom SQL-like query on the dataframe."""
        query = self.query_input.text()
        try:
            # Assuming self.data is a pandas DataFrame.
            result = self.data.query(query)
            result_str = result.to_string()  # Convert the DataFrame to a string to display in a message box or similar.
            QMessageBox.information(self, "Query Result", result_str)
        except Exception as e:
            QMessageBox.critical(self, "Query Error", str(e))

    def run_script(self):
        """Execute the provided Python script."""
        script = self.script_input.toPlainText()
        try:
            # Safe execution context needed, consider using exec() in a controlled environment
            local_vars = {}
            exec(script, globals(), local_vars)
            QMessageBox.information(self, "Script Result", "Script executed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Script Error", str(e))

    def update_data(self, dataframe):
        """Update the data and refresh column selector."""
        self.data = dataframe
        self.column_selector.clear()
        self.column_selector.addItems(self.data.columns.tolist())

    def update_selected_column(self):
        """Update statistics when a new column is selected."""
        self.selected_column = self.column_selector.currentText()
        if self.selected_column:
            self.update_stats()
            self.update_summaries()

    def update_stats(self, dataframe):
        """Update the statistics in the quick stats panel for the selected column."""
        if dataframe.empty or self.selected_column not in dataframe.columns:
            self.stats_text.setText("No data available.")
            return

        try:
            column_data = dataframe[self.selected_column]
            stats = {
                'Mean': column_data.mean(),
                'Median': column_data.median(),
                'Mode': column_data.mode().iloc[0] if not column_data.mode().empty else 'N/A',
                'Min': column_data.min(),
                'Max': column_data.max(),
                'Standard Deviation': column_data.std()
            }
            stats_str = '\n'.join([f"{key}: {value}" for key, value in stats.items()])
            self.stats_text.setText(stats_str)
        except Exception as e:
            self.stats_text.setText(f"Error calculating statistics: {e}")

    def update_summaries(self, dataframe):
        """Update the summaries in the column summaries panel."""
        if self.data.empty:
            self.summaries_text.setText("No data available.")
            return

        try:
            column_data = dataframe[self.selected_column]
            summaries = {
                'Unique Values': column_data.nunique(),
                'Missing Values': column_data.isnull().sum(),
                'Top Value': column_data.value_counts().idxmax()
            }
            summaries_str = '\n'.join([f"{key}: {value}" for key, value in summaries.items()])
            self.summaries_text.setText(summaries_str)
        except Exception as e:
            self.summaries_text.setText(f"Error calculating summaries: {e}")


def main():
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ex = DataExploration()
    ex.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
