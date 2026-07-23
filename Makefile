SHELL   := /bin/bash
PORT    ?= 8000
PYTHON  ?= python3

.DEFAULT_GOAL := help

help: ## Show this list
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-9s %s\n", $$1, $$2}'

deps: ## Install the libraries the asset builder needs
	$(PYTHON) -m pip install --user --upgrade reportlab pillow fonttools brotli

build: ## Regenerate every HTML page, sitemap, robots.txt and llms.txt
	@$(PYTHON) build.py

assets: ## Regenerate the scope PDFs, favicon and social card
	@$(PYTHON) make_assets.py

all: assets build ## Rebuild everything

check: ## Verify JSON-LD, internal links, headings, sitemap and manifest
	@$(PYTHON) check.py

serve: build ## Build, then serve on http://localhost:$(PORT)
	@echo "serving on http://localhost:$(PORT), ctrl-c to stop"
	@$(PYTHON) -m http.server $(PORT) --bind 127.0.0.1

deploy: all check ## Build, verify, commit and push to GitHub Pages
	@git add -A
	@git commit -m "Rebuild site $$(date -u +%Y-%m-%dT%H:%MZ)" || echo "nothing new to commit"
	@git push origin HEAD

dns: ## Print the DNS records to enter at Porkbun
	@$(PYTHON) check.py dns

clean: ## Remove the font cache
	@rm -rf .fontcache && echo "removed .fontcache"

.PHONY: help deps build assets all check serve deploy dns clean
