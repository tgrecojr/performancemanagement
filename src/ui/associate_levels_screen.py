"""Associate Levels CRUD screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static, Input, Label
from textual.binding import Binding
from textual.message import Message
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import AssociateLevel


class AssociateLevelForm(Container):
    """Form for adding/editing an associate level."""

    class Submitted(Message):
        """Form submitted message."""

        def __init__(
            self,
            level_id: int | None,
            description: str,
            level_indicator: int,
        ) -> None:
            self.level_id = level_id
            self.description = description
            self.level_indicator = level_indicator
            super().__init__()

    class Cancelled(Message):
        """Form cancelled message."""
        pass

    def __init__(self, level: AssociateLevel | None = None, **kwargs):
        """Initialize the form.

        Args:
            level: Optional AssociateLevel to edit. If None, creates a new level.
        """
        super().__init__(**kwargs)
        self.level = level
        self.is_edit_mode = level is not None

    def compose(self) -> ComposeResult:
        """Compose the form layout."""
        title = "Edit Associate Level" if self.is_edit_mode else "Add Associate Level"

        with ScrollableContainer(classes="form-container"):
            yield Static(title, classes="form-title")

            yield Label("Description:")
            yield Input(
                placeholder="e.g., Individual Contributor, Manager, Director",
                value=self.level.description if self.level else "",
                id="input_description",
            )

            yield Label("Level Indicator (lower = lower in hierarchy):")
            yield Input(
                placeholder="e.g., 1, 2, 3",
                value=str(self.level.level_indicator) if self.level else "",
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
        level_id = self.level.id if self.level else None
        self.post_message(self.Submitted(level_id, description, level))


class AssociateLevelsScreen(Screen):
    """Screen for managing associate levels (CRUD operations)."""

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
        with ScrollableContainer(classes="screen-container"):
            yield Static("Associate Levels Configuration", classes="screen-title")
            yield Static(
                "Manage organizational hierarchy levels",
                classes="screen-description",
            )

            with Horizontal(classes="toolbar"):
                yield Button("Add [A]", id="btn_add", variant="success")
                yield Button("Edit [E]", id="btn_edit", variant="primary")
                yield Button("Delete [D]", id="btn_delete", variant="error")
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            yield DataTable(id="levels_table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load data."""
        table = self.query_one("#levels_table", DataTable)
        table.add_columns("ID", "Description", "Level")
        table.focus()
        self.load_data()

    def load_data(self) -> None:
        """Load associate levels from the database."""
        table = self.query_one("#levels_table", DataTable)
        table.clear()

        db = get_db()
        try:
            levels = db.query(AssociateLevel).order_by(AssociateLevel.level_indicator).all()
            for level in levels:
                table.add_row(
                    str(level.id),
                    level.description,
                    str(level.level_indicator),
                    key=str(level.id),
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
        """Show form to add a new level."""
        form_container = self.query_one(".screen-container", ScrollableContainer)

        # Check if form already exists
        existing_forms = form_container.query("AssociateLevelForm")
        if existing_forms:
            return

        form = AssociateLevelForm()
        form_container.mount(form)

    def action_edit(self) -> None:
        """Show form to edit selected level."""
        table = self.query_one("#levels_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a level to edit", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            level = db.query(AssociateLevel).filter_by(id=int(row_key)).first()
            if not level:
                self.app.notify("Level not found", severity="error")
                return

            # Check if form already exists
            form_container = self.query_one(".screen-container", ScrollableContainer)
            existing_forms = form_container.query("AssociateLevelForm")
            if existing_forms:
                return

            form = AssociateLevelForm(level=level)
            form_container.mount(form)
        finally:
            db.close()

    def action_delete(self) -> None:
        """Delete the selected level."""
        table = self.query_one("#levels_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select a level to delete", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            level = db.query(AssociateLevel).filter_by(id=int(row_key)).first()
            if not level:
                self.app.notify("Level not found", severity="error")
                return

            # Check if level is in use by any associates
            if level.associates:
                self.app.notify(
                    f"Cannot delete: {len(level.associates)} associate(s) have this level",
                    severity="error",
                    timeout=5,
                )
                return

            description = level.description
            db.delete(level)
            db.commit()
            self.app.notify(f"Deleted: {description}", severity="information")
            self.load_data()
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error deleting level: {str(e)}", severity="error")
        finally:
            db.close()

    def action_refresh(self) -> None:
        """Refresh the data table."""
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()

    def on_associate_level_form_submitted(self, message: AssociateLevelForm.Submitted) -> None:
        """Handle form submission."""
        db = get_db()
        try:
            if message.level_id:
                # Edit existing
                level = db.query(AssociateLevel).filter_by(id=message.level_id).first()
                if level:
                    level.description = message.description
                    level.level_indicator = message.level_indicator
                    action = "Updated"
                else:
                    self.app.notify("Level not found", severity="error")
                    return
            else:
                # Create new
                level = AssociateLevel(
                    description=message.description,
                    level_indicator=message.level_indicator,
                )
                db.add(level)
                action = "Created"

            db.commit()
            self.app.notify(f"{action}: {level.description}", severity="success")
            self.load_data()

            # Remove the form
            form_container = self.query_one(".screen-container", ScrollableContainer)
            forms = form_container.query("AssociateLevelForm")
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
            self.app.notify(f"Error saving level: {str(e)}", severity="error")
        finally:
            db.close()

    def on_associate_level_form_cancelled(self, message: AssociateLevelForm.Cancelled) -> None:
        """Handle form cancellation."""
        form_container = self.query_one(".screen-container", ScrollableContainer)
        forms = form_container.query("AssociateLevelForm")
        for form in forms:
            form.remove()
