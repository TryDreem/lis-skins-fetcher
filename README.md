# LIS-SKINS Telegram Price Bot

A simple Telegram bot built with **aiogram** for tracking CS2 skin prices from LIS-SKINS.

The bot:

* adds skins for price tracking;
* shows your tracked skins list;
* changes target price using `/edit`;
* changes hot price notification frequency using `/time`;
* removes skins by ID;
* removes all your skins using `/masterdelete` after confirmation with `WW`;
* shows a separate locked section using `/foraristarkh`;
* registers Telegram commands so they appear when typing `/`;
* tries to delete the previous bot message before sending a new one to keep chats clean;
* checks the latest LIS-SKINS JSON price list approximately every 15 minutes;
* sends a notification when the current price is lower than or equal to the target price.

Notifications will be sent on every check while the price matches the condition.
To stop notifications, remove the skin using `/remove`.

If a skin is not found in the latest price list during a check, the bot does not overwrite `last_found_price`.
The `/skins` command will continue showing the last known price.

Using `/time`, you can choose how often to receive hot price notifications.

Notification interval:

* minimum: 15 minutes;
* maximum: 24 hours.

This does **not** change the global LIS-SKINS fetch interval.
The bot still refreshes the price list approximately every 15 minutes.

Logs show:

* when the bot fetches the LIS-SKINS price list;
* how many items were received from the price list;
* IDs of new Telegram users;
* `user_id`, `skin_id`, `skin_name`, current price, and target price during hot price notifications.

## Storage

The bot uses SQLite: `data/skins.db` by default.

Data is persisted after bot restarts.

All SQL logic is isolated in:

```text
app/storage/sqlite_storage.py
```

This allows replacing SQLite with PostgreSQL in the future without rewriting handlers or the scheduler.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and add your Telegram bot token:

```env
BOT_TOKEN=123456789:your_real_bot_token
```

Optional settings:

```env
DATABASE_PATH=data/skins.db
CHECK_INTERVAL_SECONDS=900
LIS_SKINS_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

## Running

```bash
python main.py
```

## Skin Name Format

Example:

```text
Flip Knife | Doppler Phase 4 (Factory New)
```

Important:

* use the full skin name;
* specify the phase if the skin has one;
* specify the condition, for example `Factory New`;
* `StatTrak` is currently not supported.

## Project Structure

```text
app/
  handlers/      # Telegram commands, callbacks, FSM flows
  services/      # LIS-SKINS API client and skin search logic
  storage/       # SQLite storage layer
  scheduler/     # background price checker
  keyboards/     # Telegram inline keyboards
  utils/         # price parsing and formatting
main.py          # bot entrypoint
```




# LIS-SKINS Telegram Price Bot

Простой Telegram-бот на aiogram для отслеживания цен CS2-скинов с LIS-SKINS.

Бот:
- добавляет скины для отслеживания;
- показывает список твоих скинов;
- меняет target price через `/edit`;
- меняет частоту hot price уведомлений через `/time`;
- удаляет скины по ID;
- удаляет все твои скины через `/masterdelete` после подтверждения `WW`;
- показывает отдельный locked-раздел через `/foraristarkh`;
- регистрирует команды Telegram, чтобы они появлялись при вводе `/`;
- старается удалять прошлое bot-сообщение перед отправкой нового, чтобы не засорять чат;
- примерно каждые 15 минут проверяет свежий JSON price list LIS-SKINS;
- отправляет уведомление, если текущая цена меньше или равна target price.

Уведомления будут приходить при каждой проверке, пока цена подходит под условие. Чтобы остановить уведомления, удали скин через `/remove`.

Если во время проверки скин не найден в свежем price list, бот не перезаписывает `last_found_price`. В `/skins` останется последняя известная цена.

Через `/time` можно выбрать, как часто получать hot price уведомления.
Время должно быть не меньше 15 минут и не больше 24 часов.
Это не меняет общий fetch LIS-SKINS: бот всё равно проверяет свежий price list примерно каждые 15 минут.

В логах видно:
- когда бот делает fetch LIS-SKINS price list;
- сколько items пришло в price list;
- id новых Telegram-пользователей;
- `user_id`, `skin_id`, `skin_name`, current price и target price при hot price.

## Storage

Используется SQLite: `data/skins.db` по умолчанию.

Данные сохраняются после перезапуска бота. Весь SQL вынесен в `app/storage/sqlite_storage.py`, поэтому позже storage можно заменить на PostgreSQL без переписывания handlers и scheduler.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Настройка .env

```bash
cp .env.example .env
```

Открой `.env` и укажи токен:

```env
BOT_TOKEN=123456789:your_real_bot_token
```

Опционально:

```env
DATABASE_PATH=data/skins.db
CHECK_INTERVAL_SECONDS=900
LIS_SKINS_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

## Запуск

```bash
python main.py
```

## Формат названия скина

Пример:

```text
Flip Knife | Doppler Phase 4 (Factory New)
```

Важно:
- указывай полное название;
- указывай фазу, если она есть;
- указывай качество, например `Factory New`;
- `StatTrak` пока не учитывается.

## Структура проекта

```text
app/
  handlers/      # Telegram commands, callbacks, FSM flows
  services/      # LIS-SKINS API client and skin search logic
  storage/       # SQLite storage layer
  scheduler/     # background price checker
  keyboards/     # Telegram inline keyboards
  utils/         # price parsing and formatting
main.py          # bot entrypoint
```
