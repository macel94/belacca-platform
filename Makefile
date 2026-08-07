.PHONY: init status evidence-test site-test status-test pong-test manifests manifests-native-edge validate evidence-bundle

SHELL := /usr/bin/env bash

NATIVE_EDGE_SOURCE ?= belacca-gitops/clusters/belacca-production/edge

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
	# A checked-in observation may age between hourly publications; the publish workflow validates freshness after generating a new artifact.
	if [ -d belacca-status/.git ]; then cd belacca-status && npm test && npm run check -- --allow-expired; else echo 'status repository not initialized; skipping status tests.'; fi

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

# Optional migration check; never silently skip the native edge.
manifests-native-edge:
	@if [ ! -f "$(NATIVE_EDGE_SOURCE)/kustomization.yaml" ]; then \
		echo "Native edge source is absent: $(NATIVE_EDGE_SOURCE)" >&2; \
		exit 1; \
	fi
	kubectl kustomize belacca-gitops/clusters/belacca-production >/tmp/belacca-platform-gitops-native.yaml
	kubectl kustomize "$(NATIVE_EDGE_SOURCE)" >/tmp/belacca-platform-edge-native.yaml
	@echo 'Rendered native migration manifests:'
	@wc -l /tmp/belacca-platform-{gitops-native,edge-native}.yaml

validate: site-test status-test pong-test manifests
	git diff --check
	@echo 'Workspace validation passed.'
