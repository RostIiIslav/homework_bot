class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""


class RequestExceptionError(Exception):
    """Ошибка запроса."""


class BotEmptyError(Exception):
    """Пустой список"""
