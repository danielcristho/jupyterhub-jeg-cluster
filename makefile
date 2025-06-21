# Discovery service
ds-up:
	cd discovery-service && docker compose up -d --build
	cd -

# Database migration
db-init:
	docker exec -it  discovery-api flask db init

db-migrate:
	docker exec -it  discovery-api flask db migrate -m "START MIGRATION"
	docker exec -it  discovery-api flask db upgrade
