import logging

import pytest

from slack_logger import MessageDesign, SlackHandler

logger = logging.getLogger("FormattingTests")

# Setup test handler
slack_handler = SlackHandler.dummy()
slack_handler.setLevel(logging.WARN)
logger.addHandler(slack_handler)


def test_unimpl_design() -> None:
    """Test if missing implementation in MessageDesign throws"""

    class UnimplDesign(MessageDesign):
        pass

    with pytest.raises(TypeError):
        UnimplDesign()  # type: ignore
