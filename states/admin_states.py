"""
Состояния FSM для админских функций.
"""
from aiogram.fsm.state import State, StatesGroup


class WhitelistStates(StatesGroup):
    """Состояния для управления белым списком."""
    adding_user = State()
    removing_user = State()
