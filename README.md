# ParkFlowAI

## Docker Compose

Запуск

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Postgres: localhost:5432

Данные для логина:

Админ:
- Username: `admin`
- Password: `adminadminadmin`

Пользователь:
- Username: `egor`
- Password: `123321`

Чтобы запустить полную версию приложения с детектором через docker:
`docker compose down`
`docker compose up --build backend frontend detector`