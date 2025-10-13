"""Distribution Buckets CRUD screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static, Input, Label
from textual.binding import Binding
from textual.message import Message
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import DistributionBucket
from ..reports.distribution_calculator import validate_bucket_configuration


class DistributionBucketForm(Container):
    """Form for adding/editing a distribution bucket."""

    class Submitted(Message):
        """Form submitted message."""

        def __init__(
            self,
            bucket_id: int | None,
            name: str,
            description: str,
            min_percentage: float,
            max_percentage: float,
            sort_order: int,
        ) -> None:
            self.bucket_id = bucket_id
            self.name = name
            self.description = description
            self.min_percentage = min_percentage
            self.max_percentage = max_percentage
            self.sort_order = sort_order
            super().__init__()

    class Cancelled(Message):
        """Form cancelled message."""
        pass

    def __init__(self, bucket: DistributionBucket | None = None, **kwargs):
        """Initialize the form.

        Args:
            bucket: Optional DistributionBucket to edit. If None, creates a new bucket.
        """
        super().__init__(**kwargs)
        self.bucket = bucket
        self.is_edit_mode = bucket is not None

    def compose(self) -> ComposeResult:
        """Compose the form layout."""
        title = "Edit Distribution Bucket" if self.is_edit_mode else "Add Distribution Bucket"

        with ScrollableContainer(classes="form-container"):
            yield Static(title, classes="form-title")

            yield Label("Bucket Name:")
            yield Input(
                placeholder="e.g., High Performers, Core Contributors",
                value=self.bucket.name if self.bucket else "",
                id="input_name",
            )

            yield Label("Description (optional):")
            yield Input(
                placeholder="e.g., Top tier performers including Exceptional and Very Strong",
                value=self.bucket.description if self.bucket and self.bucket.description else "",
                id="input_description",
            )

            yield Label("Minimum Percentage (0-100):")
            yield Input(
                placeholder="e.g., 15.0",
                value=str(self.bucket.min_percentage) if self.bucket else "",
                id="input_min_percentage",
            )

            yield Label("Maximum Percentage (0-100):")
            yield Input(
                placeholder="e.g., 25.0",
                value=str(self.bucket.max_percentage) if self.bucket else "",
                id="input_max_percentage",
            )

            yield Label("Sort Order (for display):")
            yield Input(
                placeholder="e.g., 1, 2, 3",
                value=str(self.bucket.sort_order) if self.bucket else "0",
                type="integer",
                id="input_sort_order",
            )

            with Horizontal(classes="form-buttons"):
                yield Button("Save", variant="primary", id="btn_save")
                yield Button("Cancel", variant="default", id="btn_cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_save":
            self._submit_form()
        elif event.button.id == "btn_cancel":
            self.post_message(self.Cancelled())

    def _submit_form(self) -> None:
        """Validate and submit the form."""
        name_input = self.query_one("#input_name", Input)
        description_input = self.query_one("#input_description", Input)
        min_input = self.query_one("#input_min_percentage", Input)
        max_input = self.query_one("#input_max_percentage", Input)
        sort_input = self.query_one("#input_sort_order", Input)

        name = name_input.value.strip()
        description = description_input.value.strip()
        min_str = min_input.value.strip()
        max_str = max_input.value.strip()
        sort_str = sort_input.value.strip()

        # Validation
        errors = []
        if not name:
            errors.append("Bucket name is required")

        min_pct = 0.0
        max_pct = 0.0
        sort_order = 0

        if not min_str:
            errors.append("Minimum percentage is required")
        else:
            try:
                min_pct = float(min_str)
                if min_pct < 0 or min_pct > 100:
                    errors.append("Minimum percentage must be between 0 and 100")
            except ValueError:
                errors.append("Minimum percentage must be a valid number")

        if not max_str:
            errors.append("Maximum percentage is required")
        else:
            try:
                max_pct = float(max_str)
                if max_pct < 0 or max_pct > 100:
                    errors.append("Maximum percentage must be between 0 and 100")
            except ValueError:
                errors.append("Maximum percentage must be a valid number")

        if min_pct > max_pct:
            errors.append("Minimum percentage cannot be greater than maximum percentage")

        if not sort_str:
            errors.append("Sort order is required")
        else:
            try:
                sort_order = int(sort_str)
            except ValueError:
                errors.append("Sort order must be a valid integer")

        if errors:
            self.app.notify("\n".join(errors), severity="error", timeout=5)
            return

        # Submit
        bucket_id = self.bucket.id if self.bucket else None
        self.post_message(
            self.Submitted(bucket_id, name, description, min_pct, max_pct, sort_order)
        )


class DistributionBucketsScreen(Screen):
    """Screen for managing distribution buckets (CRUD operations)."""

    BINDINGS = [
        Binding("a", "add", "Add", priority=True),
        Binding("e", "edit", "Edit", priority=True),
        Binding("d", "delete", "Delete", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("v", "validate", "Validate", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(classes="screen-container"):
            yield Static("Distribution Buckets Configuration", classes="screen-title")
            yield Static(
                "Manage performance rating buckets with min/max distribution targets",
                classes="screen-description",
            )

            with Horizontal(classes="toolbar"):
                yield Button("Add [A]", id="btn_add", variant="success")
                yield Button("Edit [E]", id="btn_edit", variant="primary")
                yield Button("Delete [D]", id="btn_delete", variant="error")
                yield Button("Validate [V]", id="btn_validate", variant="warning")
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            yield DataTable(id="buckets_table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load data."""
        table = self.query_one("#buckets_table", DataTable)
        table.add_columns("ID", "Name", "Min %", "Max %", "Sort", "Ratings")
        table.focus()
        self.load_data()

    def load_data(self) -> None:
        """Load distribution buckets from the database."""
        table = self.query_one("#buckets_table", DataTable)
        table.clear()

        db = get_db()
        try:
            buckets = db.query(DistributionBucket).order_by(DistributionBucket.sort_order).all()
            for bucket in buckets:
                rating_count = len(bucket.performance_ratings)
                table.add_row(
                    str(bucket.id),
                    bucket.name,
                    f"{bucket.min_percentage:.1f}",
                    f"{bucket.max_percentage:.1f}",
                    str(bucket.sort_order),
                    str(rating_count),
                    key=str(bucket.id),
                )
        finally:
            db.close()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_add":
            self.action_add()
        elif event.button.id == "btn_edit":
            self.action_edit()
        elif event.button.id == "btn_delete":
            self.action_delete()
        elif event.button.id == "btn_validate":
            self.action_validate()
        elif event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_back":
            self.action_back()

    def action_add(self) -> None:
        """Show form to add a new bucket."""
        form_container = self.query_one(".screen-container", Container)

        # Check if form already exists
        existing_forms = form_container.query("DistributionBucketForm")
        if existing_forms:
            return

        form = DistributionBucketForm()
        form_container.mount(form)

    def action_edit(self) -> None:
        """Show form to edit selected bucket."""
        table = self.query_one("#buckets_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a bucket to edit", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            bucket = db.query(DistributionBucket).filter_by(id=int(row_key)).first()
            if not bucket:
                self.app.notify("Bucket not found", severity="error")
                return

            # Check if form already exists
            form_container = self.query_one(".screen-container", Container)
            existing_forms = form_container.query("DistributionBucketForm")
            if existing_forms:
                return

            form = DistributionBucketForm(bucket=bucket)
            form_container.mount(form)
        finally:
            db.close()

    def action_delete(self) -> None:
        """Delete the selected bucket."""
        table = self.query_one("#buckets_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a bucket to delete", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            bucket = db.query(DistributionBucket).filter_by(id=int(row_key)).first()
            if not bucket:
                self.app.notify("Bucket not found", severity="error")
                return

            # Check if bucket has ratings assigned
            if bucket.performance_ratings:
                self.app.notify(
                    f"Cannot delete: {len(bucket.performance_ratings)} rating(s) assigned to this bucket",
                    severity="error",
                    timeout=5,
                )
                return

            name = bucket.name
            db.delete(bucket)
            db.commit()
            self.app.notify(f"Deleted: {name}", severity="information")
            self.load_data()
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error deleting bucket: {str(e)}", severity="error")
        finally:
            db.close()

    def action_validate(self) -> None:
        """Validate the current bucket configuration."""
        db = get_db()
        try:
            validation = validate_bucket_configuration(db)

            messages = []
            if validation['errors']:
                messages.append("ERRORS:")
                messages.extend([f"  - {err}" for err in validation['errors']])

            if validation['warnings']:
                if messages:
                    messages.append("")
                messages.append("WARNINGS:")
                messages.extend([f"  - {warn}" for warn in validation['warnings']])

            if not messages:
                self.app.notify("Configuration is valid!", severity="success")
            else:
                severity = "error" if validation['errors'] else "warning"
                self.app.notify("\n".join(messages), severity=severity, timeout=10)
        finally:
            db.close()

    def action_refresh(self) -> None:
        """Refresh the data table."""
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()

    def on_distribution_bucket_form_submitted(
        self, message: DistributionBucketForm.Submitted
    ) -> None:
        """Handle form submission."""
        db = get_db()
        try:
            if message.bucket_id:
                # Edit existing
                bucket = db.query(DistributionBucket).filter_by(id=message.bucket_id).first()
                if bucket:
                    bucket.name = message.name
                    bucket.description = message.description if message.description else None
                    bucket.min_percentage = message.min_percentage
                    bucket.max_percentage = message.max_percentage
                    bucket.sort_order = message.sort_order
                    action = "Updated"
                else:
                    self.app.notify("Bucket not found", severity="error")
                    return
            else:
                # Create new
                bucket = DistributionBucket(
                    name=message.name,
                    description=message.description if message.description else None,
                    min_percentage=message.min_percentage,
                    max_percentage=message.max_percentage,
                    sort_order=message.sort_order,
                )
                db.add(bucket)
                action = "Created"

            db.commit()
            self.app.notify(f"{action}: {bucket.name}", severity="success")
            self.load_data()

            # Remove the form
            form_container = self.query_one(".screen-container", Container)
            forms = form_container.query("DistributionBucketForm")
            for form in forms:
                form.remove()

        except IntegrityError as e:
            db.rollback()
            if "UNIQUE constraint failed" in str(e):
                if "name" in str(e):
                    self.app.notify("Error: Bucket name already exists", severity="error")
                else:
                    self.app.notify("Error: Duplicate value", severity="error")
            else:
                self.app.notify(f"Database error: {str(e)}", severity="error")
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error saving bucket: {str(e)}", severity="error")
        finally:
            db.close()

    def on_distribution_bucket_form_cancelled(
        self, message: DistributionBucketForm.Cancelled
    ) -> None:
        """Handle form cancellation."""
        form_container = self.query_one(".screen-container", Container)
        forms = form_container.query("DistributionBucketForm")
        for form in forms:
            form.remove()
