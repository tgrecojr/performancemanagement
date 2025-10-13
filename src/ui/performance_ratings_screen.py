"""Performance Ratings CRUD screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Button,
    DataTable,
    Static,
    Input,
    Label,
)
from textual.binding import Binding
from textual.message import Message
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import PerformanceRating


class PerformanceRatingForm(Container):
    """Form for adding/editing a performance rating."""

    class Submitted(Message):
        """Form submitted message."""

        def __init__(
            self,
            rating_id: int | None,
            description: str,
            level_indicator: int,
        ) -> None:
            self.rating_id = rating_id
            self.description = description
            self.level_indicator = level_indicator
            super().__init__()

    class Cancelled(Message):
        """Form cancelled message."""
        pass

    def __init__(self, rating: PerformanceRating | None = None, **kwargs):
        """Initialize the form.

        Args:
            rating: Optional PerformanceRating to edit. If None, creates a new rating.
        """
        super().__init__(**kwargs)
        self.rating = rating
        self.is_edit_mode = rating is not None

    def compose(self) -> ComposeResult:
        """Compose the form layout."""
        title = "Edit Performance Rating" if self.is_edit_mode else "Add Performance Rating"

        with ScrollableContainer(classes="form-container"):
            yield Static(title, classes="form-title")

            yield Label("Description:")
            yield Input(
                placeholder="e.g., Exceeds Expectations",
                value=self.rating.description if self.rating else "",
                id="input_description",
            )

            yield Label("Level Indicator (higher = better performance):")
            yield Input(
                placeholder="e.g., 1, 2, 3, 4",
                value=str(self.rating.level_indicator) if self.rating else "",
                type="integer",
                id="input_level_indicator",
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
        description_input = self.query_one("#input_description", Input)
        level_input = self.query_one("#input_level_indicator", Input)

        description = description_input.value.strip()
        level_str = level_input.value.strip()

        # Validation
        errors = []
        if not description:
            errors.append("Description is required")

        if not level_str:
            errors.append("Level Indicator is required")
            level = 0
        else:
            try:
                level = int(level_str)
                if level <= 0:
                    errors.append("Level Indicator must be greater than 0")
            except ValueError:
                errors.append("Level Indicator must be a valid number")
                level = 0

        if errors:
            self.app.notify("\n".join(errors), severity="error", timeout=5)
            return

        # Submit
        rating_id = self.rating.id if self.rating else None
        self.post_message(self.Submitted(rating_id, description, level))


class PerformanceRatingsScreen(Screen):
    """Screen for managing performance ratings (CRUD operations)."""

    BINDINGS = [
        Binding("a", "add", "Add", priority=True),
        Binding("e", "edit", "Edit", priority=True),
        Binding("d", "delete", "Delete", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with Container(classes="screen-container"):
            yield Static("Performance Ratings Configuration", classes="screen-title")
            yield Static(
                "Manage performance rating levels (higher level = better performance)",
                classes="screen-description",
            )

            with Horizontal(classes="toolbar"):
                yield Button("Add [A]", id="btn_add", variant="success")
                yield Button("Edit [E]", id="btn_edit", variant="primary")
                yield Button("Delete [D]", id="btn_delete", variant="error")
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            yield DataTable(id="ratings_table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load data."""
        table = self.query_one("#ratings_table", DataTable)
        table.add_columns("ID", "Description", "Level")
        table.focus()
        self.load_data()

    def load_data(self) -> None:
        """Load performance ratings from the database."""
        table = self.query_one("#ratings_table", DataTable)
        table.clear()

        db = get_db()
        try:
            ratings = db.query(PerformanceRating).order_by(PerformanceRating.level_indicator).all()
            for rating in ratings:
                table.add_row(
                    str(rating.id),
                    rating.description,
                    str(rating.level_indicator),
                    key=str(rating.id),
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
        elif event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_back":
            self.action_back()

    def action_add(self) -> None:
        """Show form to add a new rating."""
        form_container = self.query_one(".screen-container", Container)

        # Check if form already exists
        existing_forms = form_container.query("PerformanceRatingForm")
        if existing_forms:
            return

        form = PerformanceRatingForm()
        form_container.mount(form)

    def action_edit(self) -> None:
        """Show form to edit selected rating."""
        table = self.query_one("#ratings_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a rating to edit", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            rating = db.query(PerformanceRating).filter_by(id=int(row_key)).first()
            if not rating:
                self.app.notify("Rating not found", severity="error")
                return

            # Check if form already exists
            form_container = self.query_one(".screen-container", Container)
            existing_forms = form_container.query("PerformanceRatingForm")
            if existing_forms:
                return

            form = PerformanceRatingForm(rating=rating)
            form_container.mount(form)
        finally:
            db.close()

    def action_delete(self) -> None:
        """Delete the selected rating."""
        table = self.query_one("#ratings_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a rating to delete", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            rating = db.query(PerformanceRating).filter_by(id=int(row_key)).first()
            if not rating:
                self.app.notify("Rating not found", severity="error")
                return

            # Check if rating is in use by any associates
            if rating.associates:
                self.app.notify(
                    f"Cannot delete: {len(rating.associates)} associate(s) have this rating",
                    severity="error",
                    timeout=5,
                )
                return

            description = rating.description
            db.delete(rating)
            db.commit()
            self.app.notify(f"Deleted: {description}", severity="information")
            self.load_data()
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error deleting rating: {str(e)}", severity="error")
        finally:
            db.close()

    def action_refresh(self) -> None:
        """Refresh the data table."""
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()

    def on_performance_rating_form_submitted(self, message: PerformanceRatingForm.Submitted) -> None:
        """Handle form submission."""
        db = get_db()
        try:
            if message.rating_id:
                # Edit existing
                rating = db.query(PerformanceRating).filter_by(id=message.rating_id).first()
                if rating:
                    rating.description = message.description
                    rating.level_indicator = message.level_indicator
                    action = "Updated"
                else:
                    self.app.notify("Rating not found", severity="error")
                    return
            else:
                # Create new
                rating = PerformanceRating(
                    description=message.description,
                    level_indicator=message.level_indicator,
                )
                db.add(rating)
                action = "Created"

            db.commit()
            self.app.notify(f"{action}: {rating.description}", severity="success")
            self.load_data()

            # Remove the form
            form_container = self.query_one(".screen-container", Container)
            forms = form_container.query("PerformanceRatingForm")
            for form in forms:
                form.remove()

        except IntegrityError as e:
            db.rollback()
            if "UNIQUE constraint failed" in str(e):
                if "description" in str(e):
                    self.app.notify("Error: Description already exists", severity="error")
                elif "level_indicator" in str(e):
                    self.app.notify("Error: Level indicator already exists", severity="error")
                else:
                    self.app.notify("Error: Duplicate value", severity="error")
            else:
                self.app.notify(f"Database error: {str(e)}", severity="error")
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error saving rating: {str(e)}", severity="error")
        finally:
            db.close()

    def on_performance_rating_form_cancelled(self, message: PerformanceRatingForm.Cancelled) -> None:
        """Handle form cancellation."""
        form_container = self.query_one(".screen-container", Container)
        forms = form_container.query("PerformanceRatingForm")
        for form in forms:
            form.remove()
