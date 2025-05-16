"""Azure Function for SCFApp Log Alerts"""
import azure.functions as func
from src.scfapp.log_alerts.blueprints.bp_errors import bp as errors_bp
from src.scfapp.log_alerts.blueprints.bp_requests import bp as requests_bp

app = func.FunctionApp()

app.register_blueprint(errors_bp)
app.register_blueprint(requests_bp)
