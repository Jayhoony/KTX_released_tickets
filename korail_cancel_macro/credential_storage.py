from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import keyring
from keyring.errors import PasswordDeleteError


@dataclass(frozen=True)
class LoginCredentials:
    username: str
    password: str


@dataclass(frozen=True)
class PaymentCredentials:
    card_number: str
    card_password: str
    expire: str
    validation_number: str
    is_corporate: bool


@dataclass(frozen=True)
class EmailCredentials:
    password: str


class CredentialStorage:
    """Store sensitive macro credentials in the OS credential vault."""

    SERVICE_NAME = "Korail-Cancel-Macro"

    KEY_KTX_USERNAME = "ktx_username"
    KEY_KTX_PASSWORD = "ktx_password"
    KEY_KTX_CARD_NUMBER = "ktx_card_number"
    KEY_KTX_CARD_PASSWORD = "ktx_card_password"
    KEY_KTX_CARD_EXPIRE = "ktx_card_expire"
    KEY_KTX_CARD_VALIDATION = "ktx_card_validation"
    KEY_KTX_CARD_CORPORATE = "ktx_card_corporate"
    KEY_KTX_EMAIL_PASSWORD = "ktx_email_password"

    @staticmethod
    def _set(key: str, value: str) -> None:
        keyring.set_password(CredentialStorage.SERVICE_NAME, key, value)

    @staticmethod
    def _get(key: str) -> Optional[str]:
        return keyring.get_password(CredentialStorage.SERVICE_NAME, key)

    @staticmethod
    def _delete(key: str) -> None:
        try:
            keyring.delete_password(CredentialStorage.SERVICE_NAME, key)
        except PasswordDeleteError:
            pass

    @staticmethod
    def save_login(username: str, password: str) -> None:
        CredentialStorage._set(CredentialStorage.KEY_KTX_USERNAME, username)
        CredentialStorage._set(CredentialStorage.KEY_KTX_PASSWORD, password)

    @staticmethod
    def load_login() -> Optional[LoginCredentials]:
        username = CredentialStorage._get(CredentialStorage.KEY_KTX_USERNAME)
        password = CredentialStorage._get(CredentialStorage.KEY_KTX_PASSWORD)
        if username and password:
            return LoginCredentials(username=username, password=password)
        return None

    @staticmethod
    def delete_login() -> None:
        CredentialStorage._delete(CredentialStorage.KEY_KTX_USERNAME)
        CredentialStorage._delete(CredentialStorage.KEY_KTX_PASSWORD)

    @staticmethod
    def save_payment(
        card_number: str,
        card_password: str,
        expire: str,
        validation_number: str,
        is_corporate: bool,
    ) -> None:
        CredentialStorage._set(CredentialStorage.KEY_KTX_CARD_NUMBER, card_number)
        CredentialStorage._set(CredentialStorage.KEY_KTX_CARD_PASSWORD, card_password)
        CredentialStorage._set(CredentialStorage.KEY_KTX_CARD_EXPIRE, expire)
        CredentialStorage._set(CredentialStorage.KEY_KTX_CARD_VALIDATION, validation_number)
        CredentialStorage._set(CredentialStorage.KEY_KTX_CARD_CORPORATE, str(is_corporate))

    @staticmethod
    def load_payment() -> Optional[PaymentCredentials]:
        card_number = CredentialStorage._get(CredentialStorage.KEY_KTX_CARD_NUMBER)
        card_password = CredentialStorage._get(CredentialStorage.KEY_KTX_CARD_PASSWORD)
        expire = CredentialStorage._get(CredentialStorage.KEY_KTX_CARD_EXPIRE)
        validation_number = CredentialStorage._get(CredentialStorage.KEY_KTX_CARD_VALIDATION)
        is_corporate = CredentialStorage._get(CredentialStorage.KEY_KTX_CARD_CORPORATE)

        if all([card_number, card_password, expire, validation_number, is_corporate]):
            return PaymentCredentials(
                card_number=card_number or "",
                card_password=card_password or "",
                expire=expire or "",
                validation_number=validation_number or "",
                is_corporate=is_corporate == "True",
            )
        return None

    @staticmethod
    def delete_payment() -> None:
        CredentialStorage._delete(CredentialStorage.KEY_KTX_CARD_NUMBER)
        CredentialStorage._delete(CredentialStorage.KEY_KTX_CARD_PASSWORD)
        CredentialStorage._delete(CredentialStorage.KEY_KTX_CARD_EXPIRE)
        CredentialStorage._delete(CredentialStorage.KEY_KTX_CARD_VALIDATION)
        CredentialStorage._delete(CredentialStorage.KEY_KTX_CARD_CORPORATE)

    @staticmethod
    def save_email(password: str) -> None:
        CredentialStorage._set(CredentialStorage.KEY_KTX_EMAIL_PASSWORD, password)

    @staticmethod
    def load_email() -> Optional[EmailCredentials]:
        password = CredentialStorage._get(CredentialStorage.KEY_KTX_EMAIL_PASSWORD)
        if password:
            return EmailCredentials(password=password)
        return None

    @staticmethod
    def delete_email() -> None:
        CredentialStorage._delete(CredentialStorage.KEY_KTX_EMAIL_PASSWORD)

