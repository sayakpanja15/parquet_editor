from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtWidgets import QDockWidget, QTextEdit


class DockablePanels:
    def __init__(self, main_window):
        self.main_window = main_window

    def create_dockable_panel(self, title, area, widget):
        dock = QDockWidget(title, self.main_window)
        dock.setAllowedAreas(area)
        dock.setWidget(widget)
        self.main_window.addDockWidget(area, dock)
        return dock

    def add_quick_stats_panel(self):
        quick_stats_widget = QTextEdit()
        quick_stats_widget.setText("Statistics will be displayed here.")
        return self.create_dockable_panel("Quick Stats", Qt.RightDockWidgetArea, quick_stats_widget)


class ThemeSupport:
    def __init__(self, main_window):
        self.main_window = main_window
        self.init_theme_menu()

    def init_theme_menu(self):
        self.theme_menu = QMenu("Themes", self.main_window)
        self.main_window.menuBar().addMenu(self.theme_menu)

        light_theme_action = QAction("Light Theme", self.main_window)
        light_theme_action.triggered.connect(lambda: self.apply_theme('light'))
        self.theme_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Dark Theme", self.main_window)
        dark_theme_action.triggered.connect(lambda: self.apply_theme('dark'))
        self.theme_menu.addAction(dark_theme_action)

    def apply_theme(self, theme):
        if theme == 'light':
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(255, 255, 255))
            palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
            self.main_window.setPalette(palette)
        elif theme == 'dark':
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
            self.main_window.setPalette(palette)
