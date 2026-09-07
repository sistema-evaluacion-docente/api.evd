DEV = docker compose -f docker-compose.dev.yaml

dev:
	$(DEV) up

prod:
	docker compose -f docker-compose.yaml up

script:
	$(DEV) exec api_evd python scripts/$(s).py

seed:
	$(DEV) exec api_evd sh -c 'for f in seed_roles_admin seed_faculties seed_departments seed_programs seed_risk_categories seed_settings; do python scripts/$$f.py || exit 1; done'
