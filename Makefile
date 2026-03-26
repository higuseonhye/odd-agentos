.PHONY: dev prod logs shell test

dev:
	docker compose up --build

prod:
	docker compose -f docker-compose.prod.yml up -d --build

logs:
	docker compose -f docker-compose.prod.yml logs -f

shell:
	docker compose -f docker-compose.prod.yml exec api bash

test:
	python -m pytest tests agentos-sdk/tests -v
