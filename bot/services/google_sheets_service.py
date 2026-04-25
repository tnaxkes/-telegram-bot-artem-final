from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build

from config.settings import get_settings


logger = logging.getLogger(__name__)
GOOGLE_SHEETS_SCOPE = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetsLeadService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.google_sheet_id and self.settings.google_service_account_json)

    @property
    def is_ready(self) -> bool:
        return self.get_configuration_error() is None

    async def ensure_chat_id_exists(self, chat_id: int) -> bool:
        configuration_error = self.get_configuration_error()
        if configuration_error is not None:
            logger.warning('Google Sheets lead save is disabled: %s', configuration_error)
            return False
        try:
            return await asyncio.to_thread(self._ensure_chat_id_exists_sync, chat_id)
        except Exception:
            logger.exception('Failed to save tg_name=%s to Google Sheets', chat_id)
            return False

    async def read_all_chat_ids(self) -> list[int]:
        configuration_error = self.get_configuration_error()
        if configuration_error is not None:
            logger.warning('Google Sheets lead read is disabled: %s', configuration_error)
            return []
        try:
            return await asyncio.to_thread(self._read_all_chat_ids_sync)
        except Exception:
            logger.exception('Failed to read leads from Google Sheets')
            return []

    def get_configuration_error(self) -> str | None:
        if not self.settings.google_sheet_id:
            return 'GOOGLE_SHEET_ID is empty'
        if not self.settings.google_service_account_json:
            return 'GOOGLE_SERVICE_ACCOUNT_JSON is empty'
        try:
            service_account_info = self._parse_service_account_info()
        except RuntimeError as exc:
            return str(exc)

        required_keys = {'type', 'project_id', 'private_key', 'client_email', 'token_uri'}
        missing_keys = sorted(key for key in required_keys if not service_account_info.get(key))
        if missing_keys:
            return f"GOOGLE_SERVICE_ACCOUNT_JSON is missing keys: {', '.join(missing_keys)}"
        return None

    def _ensure_chat_id_exists_sync(self, chat_id: int) -> bool:
        service = self._build_service()
        sheet_title = self._get_first_sheet_title(service)
        headers = self._get_header_row(service, sheet_title)
        tg_name_index = self._ensure_tg_name_column(service, sheet_title, headers)
        existing_values = self._get_column_values(service, sheet_title, tg_name_index)
        chat_id_str = str(chat_id)
        if chat_id_str in existing_values:
            logger.info('Lead with tg_name=%s already exists in Google Sheets', chat_id_str)
            return False

        row_values = [''] * (tg_name_index + 1)
        row_values[tg_name_index] = chat_id_str
        service.spreadsheets().values().append(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"'{sheet_title}'!A:{self._column_letter(tg_name_index)}",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_values]},
        ).execute()
        logger.info('Saved lead with tg_name=%s to Google Sheets', chat_id_str)
        return True

    def _read_all_chat_ids_sync(self) -> list[int]:
        service = self._build_service()
        sheet_title = self._get_first_sheet_title(service)
        rows = self._get_all_rows(service, sheet_title)
        if not rows:
            logger.warning('Google Sheets is empty, no leads to broadcast')
            return []

        headers = [str(value).strip() for value in rows[0]]
        if 'tg_name' not in headers:
            logger.warning('Column tg_name was not found in Google Sheets, lead broadcast is skipped')
            return []

        tg_name_index = headers.index('tg_name')
        valid_chat_ids: list[int] = []
        seen_chat_ids: set[int] = set()
        for row_number, row in enumerate(rows[1:], start=2):
            raw_value = ''
            if tg_name_index < len(row):
                raw_value = str(row[tg_name_index]).strip()
            if not raw_value:
                logger.warning('Skipping Google Sheets row %s: tg_name is empty', row_number)
                continue
            if not raw_value.isdigit():
                logger.warning('Skipping Google Sheets row %s: tg_name=%r is not numeric', row_number, raw_value)
                continue
            chat_id = int(raw_value)
            if chat_id in seen_chat_ids:
                logger.info('Skipping duplicate tg_name=%s from Google Sheets row %s', chat_id, row_number)
                continue
            seen_chat_ids.add(chat_id)
            valid_chat_ids.append(chat_id)
        return valid_chat_ids

    def _build_service(self) -> Resource:
        service_account_info = self._parse_service_account_info()
        credentials = Credentials.from_service_account_info(service_account_info, scopes=GOOGLE_SHEETS_SCOPE)
        return build('sheets', 'v4', credentials=credentials, cache_discovery=False)

    def _parse_service_account_info(self) -> dict[str, Any]:
        raw_json = (self.settings.google_service_account_json or '').strip()
        if not raw_json:
            raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON is empty')

        normalized_json = raw_json.replace('\r', '')
        try:
            parsed = json.loads(normalized_json)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(normalized_json.replace('\\n', '\n'))
            except json.JSONDecodeError as exc:
                raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON') from exc

        if not isinstance(parsed, dict):
            raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON must decode to a JSON object')
        return parsed

    def _get_first_sheet_title(self, service: Resource) -> str:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=self.settings.google_sheet_id,
            fields='sheets(properties(title))',
        ).execute()
        sheets = spreadsheet.get('sheets', [])
        if not sheets:
            raise RuntimeError('Google Sheets spreadsheet has no sheets')
        return str(sheets[0]['properties']['title'])

    def _get_header_row(self, service: Resource, sheet_title: str) -> list[str]:
        response = service.spreadsheets().values().get(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"'{sheet_title}'!1:1",
        ).execute()
        values = response.get('values', [])
        if not values:
            return []
        return [str(value).strip() for value in values[0]]

    def _ensure_tg_name_column(self, service: Resource, sheet_title: str, headers: list[str]) -> int:
        if 'tg_name' in headers:
            return headers.index('tg_name')

        updated_headers = headers[:] if headers else []
        updated_headers.append('tg_name')
        service.spreadsheets().values().update(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"'{sheet_title}'!1:1",
            valueInputOption='RAW',
            body={'values': [updated_headers]},
        ).execute()
        logger.info('Column tg_name was added to Google Sheets header row')
        return len(updated_headers) - 1

    def _get_column_values(self, service: Resource, sheet_title: str, column_index: int) -> set[str]:
        column_letter = self._column_letter(column_index)
        response = service.spreadsheets().values().get(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"'{sheet_title}'!{column_letter}2:{column_letter}",
        ).execute()
        values = response.get('values', [])
        return {str(row[0]).strip() for row in values if row and str(row[0]).strip()}

    def _get_all_rows(self, service: Resource, sheet_title: str) -> list[list[Any]]:
        response = service.spreadsheets().values().get(
            spreadsheetId=self.settings.google_sheet_id,
            range=f"'{sheet_title}'",
        ).execute()
        return response.get('values', [])

    @staticmethod
    def _column_letter(column_index: int) -> str:
        result = ''
        current = column_index + 1
        while current > 0:
            current, remainder = divmod(current - 1, 26)
            result = chr(65 + remainder) + result
        return result
