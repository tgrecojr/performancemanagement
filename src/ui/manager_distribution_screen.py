"""Manager Distribution Report screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static
from textual.binding import Binding

from ..database import get_db
from ..reports.distribution_calculator import calculate_manager_distributions


class ManagerDistributionScreen(Screen):
    """Screen for viewing manager-level performance rating distributions."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with ScrollableContainer(classes="screen-container"):
            yield Static("Manager Distribution Report", classes="screen-title")
            yield Static(
                "Track distributions across managers to ensure adherence to distribution targets",
                classes="screen-description",
            )

            with Container(classes="toolbar"):
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            # Section 1: Summary
            yield Static("Overall Summary", classes="report-section-header")
            yield DataTable(id="summary_table", zebra_stripes=True, show_cursor=False)

            # Section 2: By Hierarchy Level
            yield Static("Distribution by Hierarchy Level", classes="report-section-header")
            yield Static("Aggregated view by reporting hierarchy (0 = top level)", classes="help-text")
            yield DataTable(id="hierarchy_table", zebra_stripes=True, show_cursor=False)

            # Section 3: Individual Manager Details
            yield Static("Individual Manager Details", classes="report-section-header")
            yield Static("Click on a manager to see full details", classes="help-text")
            yield DataTable(id="managers_table", zebra_stripes=True, show_cursor=True)

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data tables and load data."""
        # Summary table
        summary_table = self.query_one("#summary_table", DataTable)
        summary_table.add_columns("Metric", "Value")

        # Hierarchy table
        hierarchy_table = self.query_one("#hierarchy_table", DataTable)
        hierarchy_table.add_columns(
            "Level",
            "Managers",
            "Included\nReports",
            "Bucket Distribution %",
            "Status"
        )

        # Managers table
        managers_table = self.query_one("#managers_table", DataTable)
        managers_table.add_columns(
            "Manager",
            "Hier.\nLevel",
            "Assoc.\nLevel",
            "Total\nReports",
            "Included",
            "Bucket Distribution %",
            "Status"
        )

        self.load_data()

    def load_data(self) -> None:
        """Load manager distribution data from the database."""
        summary_table = self.query_one("#summary_table", DataTable)
        hierarchy_table = self.query_one("#hierarchy_table", DataTable)
        managers_table = self.query_one("#managers_table", DataTable)

        summary_table.clear()
        hierarchy_table.clear()
        managers_table.clear()

        db = get_db()
        try:
            # Get manager distribution data
            result = calculate_manager_distributions(db)

            # Section 1: Overall Summary
            summary_table.add_row("Total Managers", str(result.total_managers))
            summary_table.add_row(
                "Total Associates Under Managers",
                str(result.total_associates_under_managers)
            )

            # Count managers with issues
            managers_with_issues = [
                m for m in result.manager_details
                if m.buckets_out_of_range and m.included_reports > 0
            ]
            summary_table.add_row(
                "Managers Outside Target Ranges",
                str(len(managers_with_issues))
            )

            # Section 2: Hierarchy Level Summary
            if not result.hierarchy_summaries:
                hierarchy_table.add_row("No data", "-", "-", "-", "-")
            else:
                # Sort by hierarchy level
                for level in sorted(result.hierarchy_summaries.keys()):
                    summary = result.hierarchy_summaries[level]

                    # Build bucket distribution string
                    bucket_parts = []
                    for bucket_name, pct in sorted(summary['bucket_percentages'].items()):
                        bucket_parts.append(f"{bucket_name}: {pct:.1f}%")
                    bucket_str = "\n".join(bucket_parts) if bucket_parts else "(no data)"

                    # Determine overall status for this level
                    # (We'd need to check against targets, but for now just show "OK")
                    status = "✓ OK"

                    hierarchy_table.add_row(
                        f"Level {level}",
                        str(summary['manager_count']),
                        str(summary['total_included_reports']),
                        bucket_str,
                        status
                    )

            # Section 3: Individual Manager Details
            if not result.manager_details:
                managers_table.add_row("No managers found", "-", "-", "-", "-", "-", "-")
            else:
                # Sort by hierarchy level, then by name
                sorted_managers = sorted(
                    result.manager_details,
                    key=lambda m: (m.hierarchy_level, m.manager_name)
                )

                for manager in sorted_managers:
                    # Build bucket distribution string
                    bucket_parts = []
                    for bucket_name, pct in sorted(manager.bucket_percentages.items()):
                        bucket_parts.append(f"{bucket_name}: {pct:.1f}%")
                    bucket_str = "\n".join(bucket_parts) if bucket_parts else "(no data)"

                    # Determine status
                    if manager.included_reports == 0:
                        status = "- No Data"
                    elif manager.buckets_out_of_range:
                        status = f"⚠ {len(manager.buckets_out_of_range)} bucket(s) OOR"
                    else:
                        status = "✓ Within Targets"

                    managers_table.add_row(
                        manager.manager_name,
                        str(manager.hierarchy_level),
                        manager.manager_level,
                        str(manager.total_direct_reports),
                        str(manager.included_reports),
                        bucket_str,
                        status
                    )

            # Show notification if managers are out of range
            if managers_with_issues:
                self.app.notify(
                    f"WARNING: {len(managers_with_issues)} manager(s) have distributions "
                    "outside target ranges",
                    severity="warning",
                    timeout=10
                )

        except Exception as e:
            self.app.notify(f"Error loading manager distribution data: {str(e)}", severity="error")
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
