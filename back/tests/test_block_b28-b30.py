import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from back.app.services.auth_service import AuthService, MAX_FAILED_ATTEMPTS, ACCOUNT_LOCK_MINUTES
from back.app.core.exceptions import AccountLockedError, AuthenticationError


# Тест Б28 (ФТ 15) Проверка успешной авторизации с валидными данными
def test_b28_successful_login():
    # Подготовка
    mock_user_repo = MagicMock()
    auth_service = AuthService(mock_user_repo)
    
    test_user_id = 1
    test_role = "admin"

    class MockUser:
        pass
    
    mock_user = MockUser()
    mock_user.id = test_user_id
    mock_user.role = test_role
    mock_user.is_active = True
    mock_user.failed_attempts = 0
    mock_user.locked_until = None
    mock_user.password_hash = "hashed_password_123"  # Добавляем password_hash
    
    mock_user_repo.get_by_username_or_email.return_value = mock_user
    mock_user_repo.reset_login_state = MagicMock(return_value=mock_user)
    mock_user_repo.increment_failed_attempts = MagicMock()
    mock_user_repo.lock_user_until = MagicMock()
    
    # Мокаем verify_password и create_access_token
    with patch('back.app.services.auth_service.verify_password', return_value=True), \
         patch('back.app.services.auth_service.create_access_token', return_value="test_token_123"):
        
        # Выполнение
        import asyncio
        result = asyncio.run(auth_service.login("valid_user", "valid_password", "127.0.0.1"))
    
    # Проверки
    assert "access_token" in result
    assert result["access_token"] == "test_token_123"
    assert result["token_type"] == "bearer"
    assert result["role"] == test_role
    assert result["user_id"] == test_user_id
    
    # Проверяем, что сбросили состояние после успешного входа (только если были неудачные попытки)
    # В данном случае failed_attempts = 0, поэтому reset_login_state вызываться не должен
    mock_user_repo.reset_login_state.assert_not_called()
    mock_user_repo.increment_failed_attempts.assert_not_called()


# Тест Б29 (ФТ 15) Проверка неверного пароля
def test_b29_wrong_password():
    # Подготовка
    mock_user_repo = MagicMock()
    auth_service = AuthService(mock_user_repo)
    
    test_user_id = 1
    
    # Создаем объект с атрибутом failed_attempts
    class MockUser:
        def __init__(self):
            self.failed_attempts = 2
            self.password_hash = "hashed_password_123"  # Добавляем password_hash
    
    mock_user = MockUser()
    mock_user.id = test_user_id
    mock_user.is_active = True
    mock_user.locked_until = None
    
    mock_user_repo.get_by_username_or_email.return_value = mock_user
    
    # Настройка increment_failed_attempts
    def increment_attempts(user):
        user.failed_attempts += 1
        return user
    
    mock_user_repo.increment_failed_attempts.side_effect = increment_attempts
    
    # Мокаем verify_password - возвращает False (неверный пароль)
    with patch('back.app.services.auth_service.verify_password', return_value=False):
        # Выполнение и проверка
        with pytest.raises(AuthenticationError) as exc_info:
            import asyncio
            asyncio.run(auth_service.login("valid_user", "wrong_password", "127.0.0.1"))
        
        assert str(exc_info.value) == "Invalid login or password"
    
    # Проверяем, что увеличили счетчик неудачных попыток
    mock_user_repo.increment_failed_attempts.assert_called_once()
    mock_user_repo.reset_login_state.assert_not_called()
    mock_user_repo.lock_user_until.assert_not_called()


# Тест Б30 (ФТ 15) Проверка блокировки пользователя при 5 неудачных попытках
def test_b30_account_lock_after_failed_attempts():
    # Подготовка
    mock_user_repo = MagicMock()
    auth_service = AuthService(mock_user_repo)
    
    test_user_id = 1
    
    # Создаем объект с атрибутом failed_attempts
    class MockUser:
        def __init__(self):
            self.failed_attempts = MAX_FAILED_ATTEMPTS - 1  # 4 попытки
            self.password_hash = "hashed_password_123"  # Добавляем password_hash
    
    mock_user = MockUser()
    mock_user.id = test_user_id
    mock_user.is_active = True
    mock_user.locked_until = None
    
    mock_user_repo.get_by_username_or_email.return_value = mock_user
    
    # Функция increment_failed_attempts должна вернуть пользователя с failed_attempts = MAX_FAILED_ATTEMPTS
    def increment_failed_attempts(user):
        user.failed_attempts = MAX_FAILED_ATTEMPTS
        return user
    
    mock_user_repo.increment_failed_attempts.side_effect = increment_failed_attempts
    mock_user_repo.lock_user_until = MagicMock(return_value=mock_user)
    
    # Мокаем verify_password - возвращает False (неверный пароль)
    with patch('back.app.services.auth_service.verify_password', return_value=False):
        # Выполнение и проверка - должна быть ошибка блокировки
        with pytest.raises(AccountLockedError) as exc_info:
            import asyncio
            asyncio.run(auth_service.login("valid_user", "wrong_password_5th_time", "127.0.0.1"))
        
        assert "Account is temporarily locked" in str(exc_info.value)
        assert exc_info.value.locked_until is not None
    
    # Проверяем, что вызвали блокировку пользователя
    mock_user_repo.increment_failed_attempts.assert_called_once()
    mock_user_repo.lock_user_until.assert_called_once()
    
    # Проверяем параметры блокировки
    call_args = mock_user_repo.lock_user_until.call_args
    locked_user = call_args[0][0]
    locked_until = call_args[0][1]
    
    assert locked_user == mock_user
    # Проверяем, что время блокировки примерно на ACCOUNT_LOCK_MINUTES минут вперед
    now = datetime.now(timezone.utc)
    expected_until = now + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
    # Допускаем погрешность в 5 секунд
    assert abs((locked_until - expected_until).total_seconds()) < 5


# Дополнительный тест: проверка входа заблокированного пользователя
def test_b30_locked_user_cannot_login():
    """Проверка, что заблокированный пользователь не может войти"""
    # Подготовка
    mock_user_repo = MagicMock()
    auth_service = AuthService(mock_user_repo)
    
    test_user_id = 1
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    class MockUser:
        pass
    
    mock_user = MockUser()
    mock_user.id = test_user_id
    mock_user.is_active = True
    mock_user.failed_attempts = MAX_FAILED_ATTEMPTS
    mock_user.locked_until = locked_until
    mock_user.password_hash = "hashed_password_123"  # Добавляем password_hash
    
    mock_user_repo.get_by_username_or_email.return_value = mock_user
    
    # Выполнение и проверка - должна быть ошибка блокировки даже с правильным паролем
    with pytest.raises(AccountLockedError) as exc_info:
        import asyncio
        asyncio.run(auth_service.login("locked_user", "any_password", "127.0.0.1"))
    
    assert "Account is temporarily locked" in str(exc_info.value)
    assert exc_info.value.locked_until == locked_until