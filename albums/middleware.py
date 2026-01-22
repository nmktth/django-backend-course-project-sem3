import traceback
import sys
from django.utils.deprecation import MiddlewareMixin
from .models import BugReport


class AutomaticBugReportMiddleware(MiddlewareMixin):
    """
    Middleware that catches unhandled exceptions and saves them to the database as BugReports.
    """

    def process_exception(self, request, exception):
        # We only want to log server errors, not 404s (Http404 usually handled by Django)
        # But process_exception is called for unhandled exceptions.

        # Get the full traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_string = "".join(tb_list)

        # Construct a descriptive title
        error_title = f"Auto-Report: {type(exception).__name__}: {str(exception)}"
        if len(error_title) > 255:
            error_title = error_title[:252] + "..."

        # Construct detailed description with Request info
        user_info = (
            f"User: {request.user} (ID: {request.user.id})"
            if request.user.is_authenticated
            else "User: Anonymous"
        )

        description = (
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"{user_info}\n\n"
            f"Traceback:\n"
            f"{tb_string}"
        )

        # Determine user instance to save (if authenticated)
        user_instance = request.user if request.user.is_authenticated else None

        # Create BugReport
        # Note: We catch the exception, log it, but we return None so Django continues standard error handling
        # (showing 500 page or debug page)
        try:
            BugReport.objects.create(
                user=user_instance, title=error_title, description=description, status="open"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            # If logging fails, we print to stderr so we don't define the error implicitly
            print(f"Failed to create automatic bug report: {e}", file=sys.stderr)
