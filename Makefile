run_docker: docker-compose.yml
	docker compose build
	docker compose up

run_local: catan_statistics_discord/main.py
	python catan_statistics_discord/main.py

.PHONY: clean
clean_db:
	rm -rf data/catan.db

update_dependencies:
	poetry export --output=requirements/deploy.txt --without-hashes
	poetry export --output=requirements/dev.txt --without-hashes --only=dev

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  help                 Show this help message"
	@echo "  clean                Clean the processed data directory"
	@echo "  update_dependencies  Export poetry dependencies to requirements files"
	@echo "  preprocess           Run the preprocessing script"
	@echo "  train                Run the train script"
