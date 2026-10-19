.PHONY: help test test-live eval validate release version

PLUGIN_JSON := .claude-plugin/plugin.json
REMOTE      := origin
BRANCH      := main

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

validate: ## Validate plugin and marketplace manifests with Claude Code
	claude plugin validate .

test: ## Offline checks: manifests, skills, links, voice, example requests
	python3 -m unittest discover -s tests -t tests -v

test-live: ## Send every example request to VAKYN_BASE_URL (needs VAKYN_API_KEY), then the optimize loop on TweetEval irony
	python3 tests/live.py
	python3 tests/live_optimize.py

eval: ## Run skill evals in headless Claude Code, then send the requests they wrote to VAKYN_BASE_URL
	-claude plugin eval . --trust-plugin --runs $(or $(RUNS),1) -j $(or $(JOBS),4) --ablation none --allow-tools Bash Write Edit --judge-model $(or $(JUDGE),claude-sonnet-5) \
		--no-publish --keep-temp --json evals/last-$(or $(TAG),$(CASE),all).json $(if $(CASE),--case '$(CASE)') $(if $(TAG),--tag $(TAG))
	python3 tests/eval_live.py evals/last-$(or $(TAG),$(CASE),all).json

version: ## Show current version
	@grep '"version"' $(PLUGIN_JSON) | head -1 | sed 's/.*: *"\(.*\)".*/\1/'

release: validate test ## Bump version (VERSION=x.y.z or next patch), commit, tag, push
	$(eval CURRENT := $(shell grep '"version"' $(PLUGIN_JSON) | head -1 | sed 's/.*: *"\(.*\)".*/\1/'))
	$(eval NEXT := $(shell echo $(CURRENT) | awk -F. '{print $$1"."$$2"."$$3+1}'))
	$(eval VERSION := $(or $(VERSION),$(NEXT)))
	@sed -i 's/"version": *"[^"]*"/"version": "$(VERSION)"/' $(PLUGIN_JSON)
	@git add $(PLUGIN_JSON)
	@git commit -m "chore(release): v$(VERSION)"
	@git tag -a "v$(VERSION)" -m "chore(release): v$(VERSION)"
	@git push $(REMOTE) $(BRANCH) && git push $(REMOTE) "v$(VERSION)"
	@echo "Released v$(VERSION)"
