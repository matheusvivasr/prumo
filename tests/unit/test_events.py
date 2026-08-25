from prumo.core.events import Interruption, InterruptionManager


def test_no_interruption_detected_returns_none():
    manager = InterruptionManager()
    manager.register(Interruption(name="popup", detect=lambda: False, handle=lambda: None))
    assert manager.check_and_handle() is None


def test_first_matching_interruption_is_handled_and_returned():
    handled = []
    manager = InterruptionManager()
    manager.register(Interruption(name="a", detect=lambda: False, handle=lambda: handled.append("a")))
    manager.register(Interruption(name="b", detect=lambda: True, handle=lambda: handled.append("b")))
    manager.register(Interruption(name="c", detect=lambda: True, handle=lambda: handled.append("c")))

    result = manager.check_and_handle()

    assert result.name == "b"
    assert handled == ["b"]
