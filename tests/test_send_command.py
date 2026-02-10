"""Tests for SwitchBotController.send_command().

Validates HTTP retry logic, response cleanup, and error code mapping.
"""

from unittest.mock import MagicMock, patch

import main


class FakeResponse:
    """Minimal HTTP response stub for testing."""

    def __init__(self, status_code=200, text='{"statusCode":100}'):
        self.status_code = status_code
        self.text = text
        self._closed = False

    def close(self):
        self._closed = True


def _make_controller():
    return main.SwitchBotController(
        token="tok", secret="sec", device_id="dev"
    )


def test_success_on_200():
    """HTTP 200 -> 'success'."""
    ctrl = _make_controller()
    fake_resp = FakeResponse(200)
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", return_value=fake_resp):
        result = ctrl.send_command("unlock")
    assert result == "success"


def test_response_always_closed():
    """response.close() must be called even on success."""
    ctrl = _make_controller()
    fake_resp = FakeResponse(200)
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", return_value=fake_resp):
        ctrl.send_command("unlock")
    assert fake_resp._closed is True


def test_auth_error_on_401():
    """HTTP 401 -> 'auth_error', no retry."""
    ctrl = _make_controller()
    post_mock = MagicMock(return_value=FakeResponse(401))
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("lock", retries=1)
    assert result == "auth_error"
    # Must NOT retry on 401
    assert post_mock.call_count == 1


def test_api_error_after_retries_on_500():
    """HTTP 500 -> retry once, then 'api_error'."""
    ctrl = _make_controller()
    post_mock = MagicMock(return_value=FakeResponse(500))
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("unlock", retries=1)
    assert result == "api_error"
    assert post_mock.call_count == 2  # initial + 1 retry


def test_time_error_without_sync():
    """ensure_time_synced() False -> 'time_error', no HTTP call."""
    ctrl = _make_controller()
    post_mock = MagicMock()
    with patch("main.ensure_time_synced", return_value=False), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("unlock")
    assert result == "time_error"
    post_mock.assert_not_called()


def test_retry_on_none_response():
    """None response -> retry, then 'api_error'."""
    ctrl = _make_controller()
    post_mock = MagicMock(return_value=None)
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("unlock", retries=1)
    assert result == "api_error"
    assert post_mock.call_count == 2


def test_retry_on_exception():
    """Exception during post -> retry, then 'api_error'."""
    ctrl = _make_controller()
    post_mock = MagicMock(side_effect=OSError("Connection reset"))
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("lock", retries=1)
    assert result == "api_error"
    assert post_mock.call_count == 2


def test_success_after_retry():
    """First attempt fails, retry succeeds -> 'success'."""
    ctrl = _make_controller()
    responses = [FakeResponse(500), FakeResponse(200)]
    post_mock = MagicMock(side_effect=responses)
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", post_mock):
        result = ctrl.send_command("unlock", retries=1)
    assert result == "success"
    assert post_mock.call_count == 2


def test_response_closed_on_error():
    """response.close() must be called even on non-200 status."""
    ctrl = _make_controller()
    fake_resp = FakeResponse(500)
    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", return_value=fake_resp):
        ctrl.send_command("unlock", retries=0)
    assert fake_resp._closed is True


def test_response_closed_when_attribute_raises():
    """response.close() via finally even if .status_code raises."""
    ctrl = _make_controller()
    broken_resp = MagicMock()
    broken_resp.status_code = property(lambda self: (_ for _ in ()).throw(OSError))
    # Use a real object so the finally block works
    closed = []

    class BrokenResponse:
        @property
        def status_code(self):
            raise OSError("bad read")
        text = ""
        def close(self):
            closed.append(True)

    with patch("main.ensure_time_synced", return_value=True), \
         patch.object(main.urequests, "post", return_value=BrokenResponse()):
        result = ctrl.send_command("unlock", retries=0)
    assert len(closed) == 1
    assert result == "api_error"
