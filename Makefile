.PHONY: init status evidence-test site-test status-test pong-test manifests validate evidence-bundle

SHELL := /usr/bin/env bash

init:
	git submodule update --init --recursive

status:
	./scripts/status.sh

evidence-test:
	python3 -m unittest discover -s tests -v

evidence-bundle:
	./scripts/incident-evidence.sh collect --format both

update:
	git submodule update --remote --merge
	git add .gitmodules cloudnativepong francesco-belacca-site belacca-status belacca-gitops
	@echo 'Submodules updated and parent Gitlinks staged; review before committing.'

site-test:
	cd francesco-belacca-site && npm test

status-test:
	if [ -d belacca-status/.git ]; then cd belacca-status && npm test && npm run check; else echo 'status repository not initialized; skipping status tests.'; fi

pong-test:
	cd cloudnativepong && go test ./...
	cd cloudnativepong && go test -race ./...
	cd cloudnativepong && go vet ./...

manifests:
	python3 belacca-gitops/scripts/validate-catalog.py
	python3 belacca-gitops/scripts/validate-recovery-contract.py
	python3 belacca-gitops/scripts/validate-observability.py
	python3 belacca-gitops/scripts/extract-prometheus-config.py
	kubectl kustomize cloudnativepong/k8s/overlays/server >/tmp/belacca-platform-pong.yaml
	kubectl kustomize francesco-belacca-site/deploy >/tmp/belacca-platform-site.yaml
	kubectl kustomize belacca-gitops/clusters/vmi3474918 >/tmp/belacca-platform-gitops.yaml
	kubectl kustomize belacca-gitops/clusters/vmi3474918/routing >/tmp/belacca-platform-routing.yaml
	@echo 'Rendered manifests:'
	@wc -l /tmp/belacca-platform-{pong,site,gitops,routing}.yaml

validate: site-test status-test pong-test manifests
	git diff --check
	@echo 'Workspace validation passed.'
