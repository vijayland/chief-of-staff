up:
	docker-compose up -d --build
	docker-compose exec api alembic upgrade head
	@echo ""
	@echo "Frontend  →  http://localhost:3000"
	@echo "API       →  http://localhost:8000"
	@echo "API docs  →  http://localhost:8000/docs"
	@echo "Celery UI →  http://localhost:5555"

down:
	docker-compose down

logs:
	docker-compose logs -f api web worker

reset:
	docker-compose down -v
	docker-compose up -d --build
	docker-compose exec api alembic upgrade head

migrate:
	docker-compose exec api alembic upgrade head

shell-api:
	docker-compose exec api bash

shell-web:
	docker-compose exec web sh
