from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


ADD_SKIN_CALLBACK = "menu:add"
MY_SKINS_CALLBACK = "menu:skins"
EDIT_SKIN_CALLBACK = "menu:edit"
REMOVE_SKIN_CALLBACK = "menu:remove"
MASTER_DELETE_CALLBACK = "menu:masterdelete"
TIME_CALLBACK = "menu:time"
FOR_ARISTARKH_CALLBACK = "menu:foraristarkh"
DOCS_CALLBACK = "menu:docs"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Add skin — /add", callback_data=ADD_SKIN_CALLBACK),
                InlineKeyboardButton(text="My skins — /skins", callback_data=MY_SKINS_CALLBACK),
            ],
            [
                InlineKeyboardButton(text="Edit price — /edit", callback_data=EDIT_SKIN_CALLBACK),
                InlineKeyboardButton(text="Remove skin — /remove", callback_data=REMOVE_SKIN_CALLBACK),
            ],
            [
                InlineKeyboardButton(
                    text="Delete all — /masterdelete",
                    callback_data=MASTER_DELETE_CALLBACK,
                ),
            ],
            [
                InlineKeyboardButton(text="Notification time — /time", callback_data=TIME_CALLBACK),
                InlineKeyboardButton(text="Docs — /docs", callback_data=DOCS_CALLBACK),
            ],
            [
                InlineKeyboardButton(
                    text="For Aristarkh — /forAristarkh",
                    callback_data=FOR_ARISTARKH_CALLBACK,
                ),
            ],
        ]
    )
