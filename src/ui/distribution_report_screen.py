"""Distribution Report screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static
from textual.binding import Binding

from ..database import get_db
from ..reports.distribution_calculator import calculate_comprehensive_distribution


class DistributionReportScreen(Screen):
    """Screen for viewing performance rating distribution reports."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with ScrollableContainer(classes="screen-container"):
            yield Static("Performance Rating Distribution Report", classes="screen-title")
            yield Static(
                "Comprehensive distribution analysis with exclusions and bucket targets",
                classes="screen-description",
            )

            with Container(classes="toolbar"):
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            # Section 1: Headcount Summary
            yield Static("Headcount Summary", classes="report-section-header")
            yield DataTable(id="headcount_table", zebra_stripes=True, show_cursor=False)

            # Section 2: Distribution Bucket Analysis
            yield Static("Distribution Bucket Analysis", classes="report-section-header")
            yield DataTable(id="buckets_table", zebra_stripes=True, show_cursor=False)

            # Section 3: Individual Rating Distribution (Included)
            yield Static("Performance Rating Distribution (Included in Calculation)", classes="report-section-header")
            yield DataTable(id="ratings_table", zebra_stripes=True, show_cursor=False)

            # Section 4: Excluded Associates
            yield Static("Excluded from Distribution (For Visibility Only)", classes="report-section-header")
            yield DataTable(id="excluded_table", zebra_stripes=True, show_cursor=False)

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data tables and load data."""
        # Headcount table
        headcount_table = self.query_one("#headcount_table", DataTable)
        headcount_table.add_columns("Category", "Count")

        # Buckets table
        buckets_table = self.query_one("#buckets_table", DataTable)
        buckets_table.add_columns("Bucket", "Count", "Actual %", "Min %", "Max %", "Status")

        # Ratings table
        ratings_table = self.query_one("#ratings_table", DataTable)
        ratings_table.add_columns("Rating", "Count", "Percentage")

        # Excluded table
        excluded_table = self.query_one("#excluded_table", DataTable)
        excluded_table.add_columns("Category", "Count")

        self.load_data()

    def load_data(self) -> None:
        """Load distribution data from the database."""
        headcount_table = self.query_one("#headcount_table", DataTable)
        buckets_table = self.query_one("#buckets_table", DataTable)
        ratings_table = self.query_one("#ratings_table", DataTable)
        excluded_table = self.query_one("#excluded_table", DataTable)

        headcount_table.clear()
        buckets_table.clear()
        ratings_table.clear()
        excluded_table.clear()

        db = get_db()
        try:
            # Get comprehensive distribution data
            result = calculate_comprehensive_distribution(db)

            # Section 1: Headcount Summary
            headcount_table.add_row("Total Associates", str(result.total_associates))
            headcount_table.add_row(
                "Top-Level Manager (excluded)",
                str(result.top_level_manager_count)
            )
            headcount_table.add_row(
                "Excluded Ratings (e.g., 'Too New')",
                str(result.excluded_rating_count)
            )
            headcount_table.add_row("Unrated Associates", str(result.unrated_count))
            headcount_table.add_row("─" * 40, "─" * 10)
            headcount_table.add_row(
                "Included in Distribution",
                str(result.included_in_distribution_count)
            )

            # Section 2: Distribution Bucket Analysis
            if not result.bucket_distributions:
                buckets_table.add_row("No buckets configured", "-", "-", "-", "-", "-")
            else:
                for bucket in result.bucket_distributions:
                    # Determine status symbol
                    if bucket.is_within_target:
                        status = "✓ Within"
                    elif bucket.is_below_minimum:
                        status = "↓ Below Min"
                    else:  # is_above_maximum
                        status = "↑ Above Max"

                    # Build ratings breakdown string
                    ratings_str = ", ".join(
                        f"{rating}: {count}"
                        for rating, count in sorted(bucket.rating_breakdown.items())
                    ) if bucket.rating_breakdown else "(none)"

                    buckets_table.add_row(
                        f"{bucket.bucket_name}\n{ratings_str}",
                        str(bucket.count),
                        f"{bucket.percentage:.1f}%",
                        f"{bucket.min_percentage:.1f}%",
                        f"{bucket.max_percentage:.1f}%",
                        status
                    )

            # Section 3: Individual Rating Distribution (Included)
            if not result.rating_counts:
                ratings_table.add_row("No rated associates", "0", "0.0%")
            else:
                # Sort by percentage descending
                for rating, count in sorted(
                    result.rating_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    pct = result.rating_percentages.get(rating, 0.0)
                    ratings_table.add_row(
                        rating,
                        str(count),
                        f"{pct:.1f}%"
                    )

                # Total row
                ratings_table.add_row(
                    "─" * 40,
                    "─" * 10,
                    "─" * 15
                )
                ratings_table.add_row(
                    "TOTAL",
                    str(result.included_in_distribution_count),
                    "100.0%"
                )

            # Section 4: Excluded Associates
            excluded_table.add_row(
                "Top-Level Manager",
                str(result.top_level_manager_count)
            )

            if result.excluded_rating_counts:
                for rating, count in sorted(result.excluded_rating_counts.items()):
                    excluded_table.add_row(rating, str(count))
            else:
                excluded_table.add_row("(No excluded ratings)", "0")

            excluded_table.add_row("Unrated", str(result.unrated_count))

            # Show validation warnings if any buckets are out of range
            out_of_range_buckets = [
                b for b in result.bucket_distributions
                if not b.is_within_target
            ]
            if out_of_range_buckets:
                warnings = []
                for bucket in out_of_range_buckets:
                    if bucket.is_below_minimum:
                        warnings.append(
                            f"{bucket.bucket_name}: {bucket.percentage:.1f}% "
                            f"(below minimum {bucket.min_percentage:.1f}%)"
                        )
                    else:
                        warnings.append(
                            f"{bucket.bucket_name}: {bucket.percentage:.1f}% "
                            f"(above maximum {bucket.max_percentage:.1f}%)"
                        )

                self.app.notify(
                    "WARNING: Some buckets are outside target ranges:\n" + "\n".join(warnings),
                    severity="warning",
                    timeout=10
                )

        except Exception as e:
            self.app.notify(f"Error loading distribution data: {str(e)}", severity="error")
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
