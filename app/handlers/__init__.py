from app.handlers import (
    add,
    docs,
    edit,
    for_aristarkh,
    masterdelete,
    remove,
    skins,
    start,
    time_settings,
)


routers = (
    for_aristarkh.router,
    start.router,
    docs.router,
    skins.router,
    edit.router,
    remove.router,
    masterdelete.router,
    time_settings.router,
    add.router,
)


__all__ = ("routers",)
