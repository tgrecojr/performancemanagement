"""Manager Distribution Report screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static
from textual.binding import Binding

from ..database import get_db
from ..models import DistributionBucket
from ..reports.distribution_calculator import calculate_manager_distributions
from sqlalchemy import select


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

            # Section 2: Distribution by Bucket - Individual Managers
            yield Static("Manager Distribution by Bucket (%)", classes="report-section-header")
            yield Static(
                "Each cell shows the percentage of that manager's direct reports in each bucket",
                classes="help-text"
            )
            yield DataTable(id="managers_table", zebra_stripes=True, show_cursor=False)

            # Section 3: Distribution by Hierarchy Level
            yield Static("Distribution by Hierarchy Level", classes="report-section-header")
            yield Static("Aggregated view by reporting hierarchy (0 = top level)", classes="help-text")
            yield DataTable(id="hierarchy_table", zebra_stripes=True, show_cursor=False)

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data tables and load data."""
        # Summary table
        summary_table = self.query_one("#summary_table", DataTable)
        summary_table.add_columns("Metric", "Value")

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
            # Get distribution buckets (ordered)
            buckets = db.execute(
                select(DistributionBucket).order_by(DistributionBucket.sort_order)
            ).scalars().all()

            if not buckets:
                self.app.notify("No distribution buckets configured", severity="warning")
                return

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

            # Section 2: Individual Manager Distribution by Bucket
            if not result.manager_details:
                managers_table.add_row("No managers found")
            else:
                # Build column headers: Manager info + one column per bucket + status
                columns = ["Manager", "Hier.\nLevel", "Total\nReports", "Incl.\nReports"]
                for bucket in buckets:
                    # Add column with bucket name and target range
                    columns.append(f"{bucket.name}\n({bucket.min_percentage:.0f}-{bucket.max_percentage:.0f}%)")
                columns.append("Status")

                managers_table.add_columns(*columns)

                # Sort managers by hierarchy level, then by name
                sorted_managers = sorted(
                    result.manager_details,
                    key=lambda m: (m.hierarchy_level, m.manager_name)
                )

                for manager in sorted_managers:
                    # Build row data
                    row_data = [
                        manager.manager_name,
                        str(manager.hierarchy_level),
                        str(manager.total_direct_reports),
                        str(manager.included_reports),
                    ]

                    # Add bucket percentages
                    for bucket in buckets:
                        pct = manager.bucket_percentages.get(bucket.name, 0.0)

                        # Format with indicator if out of range
                        if manager.included_reports > 0:
                            if pct < bucket.min_percentage:
                                cell_text = f"↓ {pct:.1f}%"
                            elif pct > bucket.max_percentage:
                                cell_text = f"↑ {pct:.1f}%"
                            else:
                                cell_text = f"{pct:.1f}%"
                        else:
                            cell_text = "-"

                        row_data.append(cell_text)

                    # Add status column
                    if manager.included_reports == 0:
                        status = "No Data"
                    elif manager.buckets_out_of_range:
                        status = f"⚠ {len(manager.buckets_out_of_range)} OOR"
                    else:
                        status = "✓ OK"
                    row_data.append(status)

                    managers_table.add_row(*row_data)

            # Section 3: Hierarchy Level Summary
            if not result.hierarchy_summaries:
                hierarchy_table.add_row("No data")
            else:
                # Build column headers similar to managers table
                columns = ["Hierarchy\nLevel", "Managers", "Total\nIncluded"]
                for bucket in buckets:
                    columns.append(f"{bucket.name}\n({bucket.min_percentage:.0f}-{bucket.max_percentage:.0f}%)")
                columns.append("Status")

                hierarchy_table.add_columns(*columns)

                # Sort by hierarchy level
                for level in sorted(result.hierarchy_summaries.keys()):
                    summary = result.hierarchy_summaries[level]

                    row_data = [
                        f"Level {level}",
                        str(summary['manager_count']),
                        str(summary['total_included_reports']),
                    ]

                    # Add bucket percentages
                    out_of_range_count = 0
                    for bucket in buckets:
                        pct = summary['bucket_percentages'].get(bucket.name, 0.0)

                        # Check if out of range
                        if summary['total_included_reports'] > 0:
                            if pct < bucket.min_percentage:
                                cell_text = f"↓ {pct:.1f}%"
                                out_of_range_count += 1
                            elif pct > bucket.max_percentage:
                                cell_text = f"↑ {pct:.1f}%"
                                out_of_range_count += 1
                            else:
                                cell_text = f"{pct:.1f}%"
                        else:
                            cell_text = "-"

                        row_data.append(cell_text)

                    # Add status
                    if summary['total_included_reports'] == 0:
                        status = "No Data"
                    elif out_of_range_count > 0:
                        status = f"⚠ {out_of_range_count} OOR"
                    else:
                        status = "✓ OK"
                    row_data.append(status)

                    hierarchy_table.add_row(*row_data)

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
