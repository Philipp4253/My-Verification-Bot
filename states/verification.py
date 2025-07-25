"""FSM состояния для процесса верификации врачей."""

from aiogram.fsm.state import State, StatesGroup


class VerificationStates(StatesGroup):
    """Состояния процесса верификации врача."""

    entering_full_name = State()
    entering_workplace = State()
    choosing_verification_method = State()
    entering_website_url = State()
    uploading_document = State()
    processing_verification = State()
    verification_completed = State()
    verification_failed = State()

    waiting_for_start = State()
    verification_timeout = State()
    pending_removal = State()
