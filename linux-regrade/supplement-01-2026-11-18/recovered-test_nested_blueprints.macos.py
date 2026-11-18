"""Run the repository's nesting regression with the installed Werkzeug client."""
import importlib.util
from pathlib import Path

import flask
from werkzeug.test import Client


def test_nested_blueprints_with_current_werkzeug_client():
    source = Path('/Users/lyseo/sbwork/pallets__flask-4045/repo/tests/test_blueprints.py')
    spec = importlib.util.spec_from_file_location('repository_blueprint_tests', source)
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    app = flask.Flask('nested_blueprint_check')
    app.testing = True
    # Flask 2.0's client passes as_tuple, removed in installed Werkzeug 2.3.
    # Keep the repository test's assertions and use Werkzeug's client directly.
    tests.test_nested_blueprint(app, Client(app, app.response_class))
