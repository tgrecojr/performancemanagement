"""CSV Import screen for bulk loading associates."""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Static, Input, Label, Checkbox
from textual.binding import Binding
import os

from ..database import get_db
from ..utils.csv_importer import import_associates_from_csv, generate_sample_csv


class CSVImportScreen(Screen):
    """Screen for importing associates from CSV file."""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()
        with ScrollableContainer(classes="screen-container"):
            yield Static("Import Associates from CSV", classes="screen-title")
            yield Static(
                "Bulk load associates with their hierarchy from a CSV file",
                classes="screen-description",
            )

            with Container(classes="form-container"):
                yield Static("CSV File Import", classes="form-title")

                yield Label("CSV File Path:")
                yield Input(
                    placeholder="/path/to/associates.csv",
                    id="input_file_path",
                )

                yield Checkbox(
                    "Update existing associates if found",
                    value=False,
                    id="checkbox_update_existing",
                )

                yield Static(
                    "CSV Format: first_name, last_name, level, manager_first_name, manager_last_name, is_people_manager",
                    classes="help-text"
                )

                with Vertical(classes="form-buttons"):
                    yield Button("Import CSV", variant="success", id="btn_import")
                    yield Button("Generate Sample CSV", variant="primary", id="btn_generate_sample")
                    yield Button("Back [ESC]", variant="default", id="btn_back")

            yield Static("Import Results", classes="report-section-header")
            yield Static("", id="import_results", classes="import-results")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_import":
            self.action_import()
        elif event.button.id == "btn_generate_sample":
            self.action_generate_sample()
        elif event.button.id == "btn_back":
            self.action_back()

    def action_import(self) -> None:
        """Import associates from CSV file."""
        file_input = self.query_one("#input_file_path", Input)
        update_checkbox = self.query_one("#checkbox_update_existing", Checkbox)
        results_display = self.query_one("#import_results", Static)

        file_path = file_input.value.strip()

        # Validation
        if not file_path:
            self.app.notify("Please enter a CSV file path", severity="error")
            return

        # Expand ~ to home directory
        file_path = os.path.expanduser(file_path)

        if not os.path.exists(file_path):
            self.app.notify(f"File not found: {file_path}", severity="error")
            return

        if not file_path.lower().endswith('.csv'):
            self.app.notify("File must have .csv extension", severity="warning")

        # Perform import
        self.app.notify("Importing associates...", severity="information")

        db = get_db()
        try:
            result = import_associates_from_csv(
                db,
                file_path,
                update_existing=update_checkbox.value
            )

            # Build results message
            results_lines = []
            results_lines.append(f"{'='*60}")
            results_lines.append(f"Import {'SUCCESSFUL' if result.success else 'FAILED'}")
            results_lines.append(f"{'='*60}")
            results_lines.append(f"Created: {result.created_count}")
            results_lines.append(f"Updated: {result.updated_count}")
            results_lines.append(f"Skipped: {result.skipped_count}")
            results_lines.append("")

            if result.warnings:
                results_lines.append(f"Warnings ({len(result.warnings)}):")
                for warning in result.warnings[:10]:  # Show first 10
                    results_lines.append(f"  - {warning}")
                if len(result.warnings) > 10:
                    results_lines.append(f"  ... and {len(result.warnings) - 10} more warnings")
                results_lines.append("")

            if result.errors:
                results_lines.append(f"Errors ({len(result.errors)}):")
                for error in result.errors[:10]:  # Show first 10
                    results_lines.append(f"  - {error}")
                if len(result.errors) > 10:
                    results_lines.append(f"  ... and {len(result.errors) - 10} more errors")

            results_display.update("\n".join(results_lines))

            # Show notification
            if result.success:
                summary = f"Import complete: {result.created_count} created, {result.updated_count} updated"
                if result.warnings:
                    summary += f", {len(result.warnings)} warnings"
                self.app.notify(summary, severity="success", timeout=5)
            else:
                self.app.notify(
                    f"Import failed with {len(result.errors)} errors",
                    severity="error",
                    timeout=5
                )

        except Exception as e:
            results_display.update(f"ERROR: {str(e)}")
            self.app.notify(f"Import failed: {str(e)}", severity="error")
        finally:
            db.close()

    def action_generate_sample(self) -> None:
        """Generate a sample CSV file."""
        file_input = self.query_one("#input_file_path", Input)
        results_display = self.query_one("#import_results", Static)

        # Default path
        sample_path = os.path.expanduser("~/associates_sample.csv")

        # If user has entered a path, use that directory
        if file_input.value.strip():
            user_path = os.path.expanduser(file_input.value.strip())
            if os.path.isdir(user_path):
                sample_path = os.path.join(user_path, "associates_sample.csv")
            elif os.path.isdir(os.path.dirname(user_path)):
                # Use the directory part
                sample_path = os.path.join(
                    os.path.dirname(user_path),
                    "associates_sample.csv"
                )

        try:
            generate_sample_csv(sample_path)

            results_display.update(
                f"Sample CSV file created at:\n{sample_path}\n\n"
                "The file contains example data showing the required format:\n"
                "- first_name: Associate's first name\n"
                "- last_name: Associate's last name\n"
                "- level: Associate level (must match existing levels in system)\n"
                "- manager_first_name: Manager's first name (optional)\n"
                "- manager_last_name: Manager's last name (optional)\n"
                "- is_people_manager: true/yes/1/y or false (optional, defaults to false)\n\n"
                "Notes:\n"
                "- The top-level manager should have empty manager fields\n"
                "- Managers must be defined before their direct reports in the CSV\n"
                "- Level values must exactly match existing Associate Levels\n"
                "- is_people_manager is automatically set to true for anyone with direct reports"
            )

            # Update input with the generated path
            file_input.value = sample_path

            self.app.notify(
                f"Sample CSV created: {sample_path}",
                severity="success",
                timeout=5
            )

        except Exception as e:
            results_display.update(f"ERROR: Failed to create sample file\n{str(e)}")
            self.app.notify(f"Error creating sample: {str(e)}", severity="error")

    def action_back(self) -> None:
        """Go back to the main menu."""
        self.app.pop_screen()
