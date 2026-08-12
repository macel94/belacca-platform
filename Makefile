.PHONY: init status evidence-test incident-record-test site-test status-test pong-test manifests manifests-native-edge manifests-historical validate evidence-bundle

SHELL := /usr/bin/env bash

NATIVE_PRODUCTION_SOURCE ?= belacca-gitops/clusters/belacca-production
NATIVE_EDGE_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/edge
NATIVE_ROUTING_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/routing
NATIVE_OBSERVABILITY_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/observability
HISTORICAL_PRODUCTION_SOURCE ?= belacca-gitops/clusters/vmi3474918
HISTORICAL_ROUTING_SOURCE ?= $(HISTORICAL_PRODUCTION_SOURCE)/routing

init:
	git submodule update --init --recursive

status:
	./scripts/status.sh

evidence-test:
	python3 -m unittest discover -s tests -v

incident-record-test:
	python3 -m unittest discover -s tests -v

evidence-bundle:
	./scripts/incident-evidence.sh collect --format both

update:
	git submodule update --remote --merge
	git add .gitmodules cloudnativepong francesco-belacca-site belacca-status belacca-gitops belacca-infrastructure
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
	@for path in "$(NATIVE_PRODUCTION_SOURCE)" "$(NATIVE_ROUTING_SOURCE)" "$(NATIVE_OBSERVABILITY_SOURCE)"; do \
		if [ ! -f "$$path/kustomization.yaml" ]; then \
			echo "Required native production kustomization is absent: $$path/kustomization.yaml" >&2; \
			exit 1; \
		fi; \
	done
	python3 belacca-gitops/scripts/validate-catalog.py
	python3 belacca-gitops/scripts/validate-recovery-contract.py
	python3 belacca-gitops/scripts/validate-observability.py
	python3 belacca-gitops/scripts/extract-prometheus-config.py
	kubectl kustomize cloudnativepong/k8s/overlays/server >/tmp/belacca-platform-pong.yaml
	kubectl kustomize francesco-belacca-site/deploy >/tmp/belacca-platform-site.yaml
	kubectl kustomize "$(NATIVE_PRODUCTION_SOURCE)" >/tmp/belacca-platform-native-production.yaml
	kubectl kustomize "$(NATIVE_ROUTING_SOURCE)" >/tmp/belacca-platform-native-routing.yaml
	kubectl kustomize "$(NATIVE_OBSERVABILITY_SOURCE)" >/tmp/belacca-platform-native-observability.yaml
	@echo 'Rendered application and native production manifests:'
	@wc -l /tmp/belacca-platform-{pong,site,native-production,native-routing,native-observability}.yaml

# Explicit audit-only check for the retired old-production GitOps tree.
manifests-historical:
	kubectl kustomize "$(HISTORICAL_PRODUCTION_SOURCE)" >/tmp/belacca-platform-historical-gitops.yaml
	kubectl kustomize "$(HISTORICAL_ROUTING_SOURCE)" >/tmp/belacca-platform-historical-routing.yaml
	@echo 'Rendered historical/retired manifests (not live production):'
	@wc -l /tmp/belacca-platform-{historical-gitops,historical-routing}.yaml

# Compatibility check for callers that specifically validate the native edge.
# The native production root is rendered here as well; this target never falls
# back to the retired tree or silently skips a missing native edge.
manifests-native-edge:
	@for path in "$(NATIVE_PRODUCTION_SOURCE)" "$(NATIVE_EDGE_SOURCE)"; do \
		if [ ! -f "$$path/kustomization.yaml" ]; then \
			echo "Required native production kustomization is absent: $$path/kustomization.yaml" >&2; \
			exit 1; \
		fi; \
	done
	kubectl kustomize "$(NATIVE_PRODUCTION_SOURCE)" >/tmp/belacca-platform-gitops-native.yaml
	kubectl kustomize "$(NATIVE_EDGE_SOURCE)" >/tmp/belacca-platform-edge-native.yaml
	@echo 'Rendered native production and edge manifests:'
	@wc -l /tmp/belacca-platform-{gitops-native,edge-native}.yaml

validate: site-test status-test pong-test manifests
	git diff --check
	@echo 'Workspace validation passed.'
