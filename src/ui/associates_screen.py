"""Associates CRUD screen."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Button, DataTable, Static, Input, Label, Select
from textual.binding import Binding
from textual.message import Message
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import Associate, AssociateLevel


class AssociateForm(Container):
    """Form for adding/editing an associate."""

    class Submitted(Message):
        """Form submitted message."""

        def __init__(
            self,
            associate_id: int | None,
            first_name: str,
            last_name: str,
            associate_level_id: int,
            manager_id: int | None,
            is_people_manager: bool,
        ) -> None:
            self.associate_id = associate_id
            self.first_name = first_name
            self.last_name = last_name
            self.associate_level_id = associate_level_id
            self.manager_id = manager_id
            self.is_people_manager = is_people_manager
            super().__init__()

    class Cancelled(Message):
        """Form cancelled message."""
        pass

    def __init__(self, associate: Associate | None = None, **kwargs):
        """Initialize the form.

        Args:
            associate: Optional Associate to edit. If None, creates a new associate.
        """
        super().__init__(**kwargs)
        self.associate = associate
        self.is_edit_mode = associate is not None

    def compose(self) -> ComposeResult:
        """Compose the form layout."""
        title = "Edit Associate" if self.is_edit_mode else "Add Associate"

        # Load levels and managers for dropdowns
        db = get_db()
        try:
            levels = db.query(AssociateLevel).order_by(AssociateLevel.level_indicator).all()
            level_options = [(f"{level.description} (Level {level.level_indicator})", str(level.id)) for level in levels]

            # For managers, get all associates who are people managers
            managers = db.query(Associate).filter_by(is_people_manager=True).order_by(Associate.last_name, Associate.first_name).all()
            manager_options = [("(No Manager)", "0")] + [(f"{mgr.full_name}", str(mgr.id)) for mgr in managers]
        finally:
            db.close()

        with ScrollableContainer(classes="form-container"):
            yield Static(title, classes="form-title")

            yield Label("First Name:")
            yield Input(
                placeholder="First name",
                value=self.associate.first_name if self.associate else "",
                id="input_first_name",
            )

            yield Label("Last Name:")
            yield Input(
                placeholder="Last name",
                value=self.associate.last_name if self.associate else "",
                id="input_last_name",
            )

            yield Label("Associate Level:")
            yield Select(
                options=level_options,
                value=str(self.associate.associate_level_id) if self.associate else Select.BLANK,
                id="select_level",
                allow_blank=False,
            )

            yield Label("Manager:")
            yield Select(
                options=manager_options,
                value=str(self.associate.manager_id) if self.associate and self.associate.manager_id else "0",
                id="select_manager",
                allow_blank=False,
            )

            yield Label("Is People Manager:")
            yield Select(
                options=[("No", "false"), ("Yes", "true")],
                value="true" if self.associate and self.associate.is_people_manager else "false",
                id="select_is_manager",
                allow_blank=False,
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
        first_name_input = self.query_one("#input_first_name", Input)
        last_name_input = self.query_one("#input_last_name", Input)
        level_select = self.query_one("#select_level", Select)
        manager_select = self.query_one("#select_manager", Select)
        is_manager_select = self.query_one("#select_is_manager", Select)

        first_name = first_name_input.value.strip()
        last_name = last_name_input.value.strip()

        # Validation
        errors = []
        if not first_name:
            errors.append("First name is required")
        if not last_name:
            errors.append("Last name is required")
        if level_select.value == Select.BLANK:
            errors.append("Associate level is required")

        if errors:
            self.app.notify("\n".join(errors), severity="error", timeout=5)
            return

        # Parse values
        level_id = int(level_select.value)
        manager_id = int(manager_select.value) if manager_select.value != "0" else None
        is_people_manager = is_manager_select.value == "true"

        # Submit
        associate_id = self.associate.id if self.associate else None
        self.post_message(
            self.Submitted(
                associate_id,
                first_name,
                last_name,
                level_id,
                manager_id,
                is_people_manager,
            )
        )


class AssociatesScreen(Screen):
    """Screen for managing associates (CRUD operations)."""

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
            yield Static("Associates Configuration", classes="screen-title")
            yield Static(
                "Manage employees (Note: Performance ratings are assigned separately)",
                classes="screen-description",
            )

            with Horizontal(classes="toolbar"):
                yield Button("Add [A]", id="btn_add", variant="success")
                yield Button("Edit [E]", id="btn_edit", variant="primary")
                yield Button("Delete [D]", id="btn_delete", variant="error")
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")

            yield DataTable(id="associates_table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load data."""
        table = self.query_one("#associates_table", DataTable)
        table.add_columns("ID", "Name", "Level", "Manager", "Is Mgr")
        table.focus()
        self.load_data()

    def load_data(self) -> None:
        """Load associates from the database."""
        table = self.query_one("#associates_table", DataTable)
        table.clear()

        db = get_db()
        try:
            associates = db.query(Associate).order_by(Associate.last_name, Associate.first_name).all()
            for assoc in associates:
                table.add_row(
                    str(assoc.id),
                    assoc.full_name,
                    assoc.associate_level.description if assoc.associate_level else "N/A",
                    assoc.manager.full_name if assoc.manager else "(None)",
                    "Yes" if assoc.is_people_manager else "No",
                    key=str(assoc.id),
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
        """Show form to add a new associate."""
        form_container = self.query_one(".screen-container", Container)

        # Check if form already exists
        existing_forms = form_container.query("AssociateForm")
        if existing_forms:
            return

        form = AssociateForm()
        form_container.mount(form)

    def action_edit(self) -> None:
        """Show form to edit selected associate."""
        table = self.query_one("#associates_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select an associate to edit", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            associate = db.query(Associate).filter_by(id=int(row_key)).first()
            if not associate:
                self.app.notify("Associate not found", severity="error")
                return

            # Check if form already exists
            form_container = self.query_one(".screen-container", Container)
            existing_forms = form_container.query("AssociateForm")
            if existing_forms:
                return

            form = AssociateForm(associate=associate)
            form_container.mount(form)
        finally:
            db.close()

    def action_delete(self) -> None:
        """Delete the selected associate."""
        table = self.query_one("#associates_table", DataTable)

        if table.cursor_row is None or not table.rows:
            self.app.notify("Please select an associate to delete", severity="warning")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        db = get_db()
        try:
            associate = db.query(Associate).filter_by(id=int(row_key)).first()
            if not associate:
                self.app.notify("Associate not found", severity="error")
                return

            # Check if associate has direct reports
            if associate.direct_reports:
                self.app.notify(
                    f"Cannot delete: {len(associate.direct_reports)} associate(s) report to this person",
                    severity="error",
                    timeout=5,
                )
                return

            full_name = associate.full_name
            db.delete(associate)
            db.commit()
            self.app.notify(f"Deleted: {full_name}", severity="information")
            self.load_data()
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error deleting associate: {str(e)}", severity="error")
        finally:
            db.close()

    def action_refresh(self) -> None:
        """Refresh the data table."""
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()

    def on_associate_form_submitted(self, message: AssociateForm.Submitted) -> None:
        """Handle form submission."""
        db = get_db()
        try:
            if message.associate_id:
                # Edit existing
                associate = db.query(Associate).filter_by(id=message.associate_id).first()
                if associate:
                    associate.first_name = message.first_name
                    associate.last_name = message.last_name
                    associate.associate_level_id = message.associate_level_id
                    associate.manager_id = message.manager_id
                    associate.is_people_manager = message.is_people_manager
                    action = "Updated"
                else:
                    self.app.notify("Associate not found", severity="error")
                    return
            else:
                # Create new
                associate = Associate(
                    first_name=message.first_name,
                    last_name=message.last_name,
                    associate_level_id=message.associate_level_id,
                    manager_id=message.manager_id,
                    is_people_manager=message.is_people_manager,
                )
                db.add(associate)
                action = "Created"

            db.commit()
            self.app.notify(f"{action}: {associate.full_name}", severity="success")
            self.load_data()

            # Remove the form
            form_container = self.query_one(".screen-container", Container)
            forms = form_container.query("AssociateForm")
            for form in forms:
                form.remove()

        except Exception as e:
            db.rollback()
            self.app.notify(f"Error saving associate: {str(e)}", severity="error")
        finally:
            db.close()

    def on_associate_form_cancelled(self, message: AssociateForm.Cancelled) -> None:
        """Handle form cancellation."""
        form_container = self.query_one(".screen-container", Container)
        forms = form_container.query("AssociateForm")
        for form in forms:
            form.remove()
