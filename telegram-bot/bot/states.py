from aiogram.fsm.state import State, StatesGroup


class ProductForm(StatesGroup):
    choosing_store = State()
    waiting_photo = State()
    waiting_price = State()
    waiting_title = State()
    confirmation = State()
