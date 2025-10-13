"""Distribution Report screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Button, DataTable, Static
from textual.binding import Binding

from ..database import get_db
from ..reports import (
    get_total_headcount,
    calculate_rating_distribution_percentages,
    get_level_distribution_summary,
)


class DistributionReportScreen(Screen):
    """Screen for viewing performance rating distribution reports."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(classes="screen-container"):
            yield Static("Performance Rating Distribution Report", classes="screen-title")
            yield Static(
                "View distribution of performance ratings across the organization",
                classes="screen-description",
            )

            with Container(classes="toolbar"):
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            yield Static("Overall Distribution", classes="report-section-header")
            yield DataTable(id="overall_table", zebra_stripes=True)

            yield Static("Distribution by Level", classes="report-section-header")
            yield DataTable(id="by_level_table", zebra_stripes=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data tables and load data."""
        overall_table = self.query_one("#overall_table", DataTable)
        overall_table.add_columns("Performance Rating", "Count", "Percentage")

        by_level_table = self.query_one("#by_level_table", DataTable)
        by_level_table.add_columns("Level", "Rating", "Count", "% of Level")

        self.load_data()

    def load_data(self) -> None:
        """Load distribution data from the database."""
        overall_table = self.query_one("#overall_table", DataTable)
        by_level_table = self.query_one("#by_level_table", DataTable)

        overall_table.clear()
        by_level_table.clear()

        db = get_db()
        try:
            # Overall distribution
            total = get_total_headcount(db)
            percentages = calculate_rating_distribution_percentages(db)

            if total == 0:
                overall_table.add_row("No data", "0", "0.0%")
            else:
                # Sort by rating level (would need to join to get level_indicator, for now sort by name)
                for rating, pct in sorted(percentages.items()):
                    count = int(total * pct / 100)  # Back-calculate count from percentage
                    overall_table.add_row(
                        rating,
                        str(count),
                        f"{pct:.1f}%"
                    )

                # Add total row
                overall_table.add_row(
                    "TOTAL",
                    str(total),
                    "100.0%",
                )

            # Distribution by level
            level_summary = get_level_distribution_summary(db)

            if not level_summary:
                by_level_table.add_row("No data", "-", "0", "0.0%")
            else:
                # Sort by level indicator
                for level_desc, data in sorted(level_summary.items(), key=lambda x: x[1]['level_indicator']):
                    if not data['rating_counts']:
                        by_level_table.add_row(
                            level_desc,
                            "(None)",
                            str(data['total_associates']),
                            "-"
                        )
                    else:
                        # Show each rating for this level
                        first_row = True
                        for rating, count in sorted(data['rating_counts'].items()):
                            pct = data['rating_percentages'].get(rating, 0)
                            by_level_table.add_row(
                                level_desc if first_row else "",
                                rating,
                                str(count),
                                f"{pct:.1f}%"
                            )
                            first_row = False

                        # Show unrated count if any
                        if data['unrated_associates'] > 0:
                            by_level_table.add_row(
                                "",
                                "(Unrated)",
                                str(data['unrated_associates']),
                                "-"
                            )

        finally:
            db.close()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_back":
            self.action_back()

    def action_refresh(self) -> None:
        """Refresh the data tables."""
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()
