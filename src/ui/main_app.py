"""Main application for Performance Management TUI."""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static
from textual.binding import Binding
from textual.screen import Screen

from ..database import init_db
from .performance_ratings_screen import PerformanceRatingsScreen
from .associate_levels_screen import AssociateLevelsScreen
from .associates_screen import AssociatesScreen
from .distribution_report_screen import DistributionReportScreen
from .manager_distribution_screen import ManagerDistributionScreen
from .rating_input_screen import RatingInputScreen
from .distribution_buckets_screen import DistributionBucketsScreen
from .csv_import_screen import CSVImportScreen


class MainMenuScreen(Screen):
    """Main menu screen with navigation to different sections."""

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main menu layout."""
        yield Header()
        yield Container(
            Static("Performance Management System", classes="title"),
            Static("Configuration", classes="section-header"),
            Vertical(
                Button("Performance Ratings", id="btn_ratings", variant="primary"),
                Button("Distribution Buckets", id="btn_buckets", variant="primary"),
                Button("Associate Levels", id="btn_levels", variant="primary"),
                Button("Associates", id="btn_associates", variant="primary"),
                classes="button-group",
            ),
            Static("Data Input", classes="section-header"),
            Vertical(
                Button("Import Associates (CSV)", id="btn_import_csv", variant="success"),
                Button("Enter Performance Ratings", id="btn_input_ratings", variant="success"),
                classes="button-group",
            ),
            Static("Reports", classes="section-header"),
            Vertical(
                Button("Distribution Reports", id="btn_reports", variant="warning"),
                Button("Manager Distribution Reports", id="btn_manager_reports", variant="warning"),
                classes="button-group",
            ),
            classes="main-menu",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_ratings":
            self.app.push_screen(PerformanceRatingsScreen())
        elif event.button.id == "btn_buckets":
            self.app.push_screen(DistributionBucketsScreen())
        elif event.button.id == "btn_levels":
            self.app.push_screen(AssociateLevelsScreen())
        elif event.button.id == "btn_associates":
            self.app.push_screen(AssociatesScreen())
        elif event.button.id == "btn_import_csv":
            self.app.push_screen(CSVImportScreen())
        elif event.button.id == "btn_input_ratings":
            self.app.push_screen(RatingInputScreen())
        elif event.button.id == "btn_reports":
            self.app.push_screen(DistributionReportScreen())
        elif event.button.id == "btn_manager_reports":
            self.app.push_screen(ManagerDistributionScreen())


class PerformanceManagementApp(App):
    """Main application class."""

    CSS_PATH = "styles.css"
    TITLE = "Performance Management System"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    def on_mount(self) -> None:
        """Initialize the database when the app starts."""
        init_db()
        self.push_screen(MainMenuScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


def main():
    """Run the application."""
    app = PerformanceManagementApp()
    app.run()


if __name__ == "__main__":
    main()
