"""mysite.views

这个项目的实际业务视图在 image_search.views。
保留该模块仅用于兼容/避免错误导入；不在此重复实现逻辑。
"""

from image_search.views import (  # noqa: F401
    index,
    results,
    history,
    history_detail,
    favorites,
    api_history_remove,
    api_favorite_add,
    api_favorite_remove,
)
