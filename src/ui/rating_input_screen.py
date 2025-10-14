"""Performance Rating Data Input screen for bulk assignment by level."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Button,
    DataTable,
    Static,
    Select,
    Label,
)
from textual.binding import Binding
from textual.message import Message
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import Associate, AssociateLevel, PerformanceRating


class RatingInputScreen(Screen):
    """Screen for bulk assignment of performance ratings to associates by level."""

    BINDINGS = [
        Binding("s", "save", "Save All", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("escape", "back", "Back", priority=True),
    ]

    def __init__(self, **kwargs):
        """Initialize the screen."""
        super().__init__(**kwargs)
        self.selected_level_id = None
        self.rating_changes = {}  # Track changes: {associate_id: rating_id}
        self.available_ratings = {}  # Cache: {rating_id: description}

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with ScrollableContainer(classes="screen-container"):
            yield Static("Performance Rating Data Input", classes="screen-title")
            yield Static(
                "Select a level to view and assign performance ratings to associates",
                classes="screen-description",
            )

            with Horizontal(classes="filter-bar"):
                yield Label("Filter by Level:")
                yield Select(
                    options=[("All Levels", None)],
                    id="level_filter",
                    allow_blank=False,
                )

            with Horizontal(classes="toolbar"):
                yield Button("Save All [S]", id="btn_save", variant="success")
                yield Button("Refresh [R]", id="btn_refresh", variant="default")
                yield Button("Back [ESC]", id="btn_back", variant="default")
                yield Static("", id="changes_indicator", classes="changes-indicator")

            yield DataTable(id="associates_table", zebra_stripes=True, cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        """Set up the data table and load data."""
        self._load_levels()
        self._load_ratings()
        table = self.query_one("#associates_table", DataTable)
        table.add_columns("ID", "Name", "Level", "Current Rating", "New Rating")
        table.focus()
        self.load_data()

    def _load_levels(self) -> None:
        """Load available associate levels into the filter dropdown."""
        level_select = self.query_one("#level_filter", Select)
        db = get_db()
        try:
            levels = db.query(AssociateLevel).order_by(AssociateLevel.level_indicator).all()
            options = [("All Levels", None)]
            options.extend([(level.description, str(level.id)) for level in levels])
            level_select.set_options(options)
        finally:
            db.close()

    def _load_ratings(self) -> None:
        """Load available performance ratings for quick lookup."""
        db = get_db()
        try:
            ratings = db.query(PerformanceRating).order_by(PerformanceRating.level_indicator).all()
            self.available_ratings = {rating.id: rating.description for rating in ratings}
        finally:
            db.close()

    def load_data(self) -> None:
        """Load associates from the database based on selected level."""
        table = self.query_one("#associates_table", DataTable)
        table.clear()

        db = get_db()
        try:
            query = db.query(Associate)

            # Filter by level if selected
            if self.selected_level_id:
                query = query.filter(Associate.associate_level_id == self.selected_level_id)

            # Order by level, then name
            associates = query.join(AssociateLevel).order_by(
                AssociateLevel.level_indicator,
                Associate.last_name,
                Associate.first_name
            ).all()

            for associate in associates:
                current_rating = (
                    associate.performance_rating.description
                    if associate.performance_rating
                    else "(Not Set)"
                )

                # Check if there's a pending change
                new_rating = ""
                if associate.id in self.rating_changes:
                    new_rating_id = self.rating_changes[associate.id]
                    if new_rating_id is None:
                        new_rating = "(Clear Rating)"
                    else:
                        new_rating = self.available_ratings.get(new_rating_id, "")

                table.add_row(
                    str(associate.id),
                    associate.full_name,
                    associate.associate_level.description,
                    current_rating,
                    new_rating,
                    key=str(associate.id),
                )
        finally:
            db.close()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle level filter changes."""
        if event.select.id == "level_filter":
            self.selected_level_id = int(event.value) if event.value else None
            self.rating_changes.clear()  # Clear changes when switching levels
            self._update_changes_indicator()
            self.load_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to edit rating."""
        table = self.query_one("#associates_table", DataTable)

        if event.cursor_row is None:
            return

        row_data = table.get_row_at(event.cursor_row)
        associate_id = int(row_data[0])
        associate_name = row_data[1]
        current_rating = row_data[3]

        # Show rating selection modal
        self._show_rating_selector(associate_id, associate_name, current_rating)

    def _show_rating_selector(self, associate_id: int, associate_name: str, current_rating: str) -> None:
        """Show a modal to select a new rating for the associate."""
        # Create a modal-like container
        container = self.query_one(".screen-container", Container)

        # Check if selector already exists
        existing = container.query("RatingSelector")
        if existing:
            return

        selector = RatingSelector(
            associate_id=associate_id,
            associate_name=associate_name,
            current_rating=current_rating,
            available_ratings=self.available_ratings,
        )
        container.mount(selector)

    def on_rating_selector_rating_selected(self, message) -> None:
        """Handle rating selection from the modal."""
        self.rating_changes[message.associate_id] = message.rating_id
        self._update_changes_indicator()
        self.load_data()

        # Remove the selector
        container = self.query_one(".screen-container", Container)
        selectors = container.query("RatingSelector")
        for selector in selectors:
            selector.remove()

    def on_rating_selector_cancelled(self, message) -> None:
        """Handle rating selector cancellation."""
        container = self.query_one(".screen-container", Container)
        selectors = container.query("RatingSelector")
        for selector in selectors:
            selector.remove()

    def _update_changes_indicator(self) -> None:
        """Update the changes indicator to show pending changes."""
        indicator = self.query_one("#changes_indicator", Static)
        count = len(self.rating_changes)
        if count > 0:
            indicator.update(f"Pending changes: {count}")
        else:
            indicator.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_save":
            self.action_save()
        elif event.button.id == "btn_refresh":
            self.action_refresh()
        elif event.button.id == "btn_back":
            self.action_back()

    def action_save(self) -> None:
        """Save all pending rating changes."""
        if not self.rating_changes:
            self.app.notify("No changes to save", severity="information")
            return

        db = get_db()
        try:
            saved_count = 0
            for associate_id, rating_id in self.rating_changes.items():
                associate = db.query(Associate).filter_by(id=associate_id).first()
                if associate:
                    associate.performance_rating_id = rating_id
                    saved_count += 1

            db.commit()
            self.app.notify(
                f"Successfully saved {saved_count} rating assignment(s)",
                severity="success"
            )
            self.rating_changes.clear()
            self._update_changes_indicator()
            self.load_data()
        except Exception as e:
            db.rollback()
            self.app.notify(f"Error saving ratings: {str(e)}", severity="error")
        finally:
            db.close()

    def action_refresh(self) -> None:
        """Refresh the data table."""
        if self.rating_changes:
            # Warn about unsaved changes
            self.app.notify(
                "Warning: You have unsaved changes that will be lost",
                severity="warning",
                timeout=5
            )
        self.rating_changes.clear()
        self._update_changes_indicator()
        self.load_data()
        self.app.notify("Data refreshed", severity="information")

    def action_back(self) -> None:
        """Go back to the main menu."""
        if self.rating_changes:
            self.app.notify(
                "Warning: You have unsaved changes. Save or refresh before leaving.",
                severity="warning",
                timeout=5
            )
            return
        self.app.pop_screen()


class RatingSelector(Container):
    """Modal-like widget for selecting a performance rating."""

    class RatingSelected(Message):
        """Rating selected message."""
        def __init__(self, associate_id: int, rating_id: int | None) -> None:
            self.associate_id = associate_id
            self.rating_id = rating_id
            super().__init__()

    class Cancelled(Message):
        """Selection cancelled message."""
        pass

    def __init__(
        self,
        associate_id: int,
        associate_name: str,
        current_rating: str,
        available_ratings: dict,
        **kwargs
    ):
        """Initialize the rating selector.

        Args:
            associate_id: ID of the associate
            associate_name: Full name of the associate
            current_rating: Current rating description
            available_ratings: Dict of rating_id -> description
        """
        super().__init__(**kwargs)
        self.associate_id = associate_id
        self.associate_name = associate_name
        self.current_rating = current_rating
        self.available_ratings = available_ratings

    def compose(self) -> ComposeResult:
        """Compose the selector layout."""
        with ScrollableContainer(classes="modal-container"):
            yield Static(f"Select Rating for {self.associate_name}", classes="modal-title")
            yield Static(f"Current: {self.current_rating}", classes="modal-subtitle")

            with Vertical(classes="rating-buttons"):
                # Add button to clear rating
                yield Button("(Clear Rating)", id="rating_none", variant="default")

                # Add button for each available rating
                db = get_db()
                try:
                    ratings = db.query(PerformanceRating).order_by(
                        PerformanceRating.level_indicator.desc()
                    ).all()
                    for rating in ratings:
                        yield Button(
                            f"{rating.description} (Level {rating.level_indicator})",
                            id=f"rating_{rating.id}",
                            variant="primary"
                        )
                finally:
                    db.close()

                yield Button("Cancel", id="btn_cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_cancel":
            self.post_message(self.Cancelled())
        elif event.button.id == "rating_none":
            self.post_message(self.RatingSelected(self.associate_id, None))
        elif event.button.id.startswith("rating_"):
            rating_id = int(event.button.id.replace("rating_", ""))
            self.post_message(self.RatingSelected(self.associate_id, rating_id))
