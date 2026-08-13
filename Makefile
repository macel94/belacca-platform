.PHONY: init status evidence-test drill-test drill-validate policy-test site-test status-test pong-test manifests manifests-native-edge validate evidence-bundle

SHELL := /usr/bin/env bash

NATIVE_PRODUCTION_SOURCE ?= belacca-gitops/clusters/belacca-production
NATIVE_EDGE_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/edge
NATIVE_ROUTING_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/routing
NATIVE_OBSERVABILITY_SOURCE ?= $(NATIVE_PRODUCTION_SOURCE)/observability
NATIVE_PONG_SOURCE ?= cloudnativepong/k8s/overlays/native-staging
NATIVE_SITE_SOURCE ?= francesco-belacca-site/deploy
NATIVE_KUSTOMIZATIONS := \
	$(NATIVE_PRODUCTION_SOURCE) \
	$(NATIVE_PRODUCTION_SOURCE)/flux-system \
	$(NATIVE_PRODUCTION_SOURCE)/secrets \
	$(NATIVE_PRODUCTION_SOURCE)/longhorn \
	$(NATIVE_EDGE_SOURCE) \
	$(NATIVE_PRODUCTION_SOURCE)/cert-manager \
	$(NATIVE_PRODUCTION_SOURCE)/tls \
	$(NATIVE_ROUTING_SOURCE) \
	$(NATIVE_PRODUCTION_SOURCE)/dex \
	$(NATIVE_PRODUCTION_SOURCE)/analytics \
	$(NATIVE_OBSERVABILITY_SOURCE) \
	$(NATIVE_PRODUCTION_SOURCE)/headlamp \
	$(NATIVE_PRODUCTION_SOURCE)/flux-web

init:
	git submodule update --init --recursive

status:
	./scripts/status.sh

evidence-test:
	python3 -m unittest discover -s tests -v

drill-test:
	python3 -m unittest tests.test_controlled_drill -v

drill-validate:
	@test -n "$(RECORD)" || { echo 'Usage: make drill-validate RECORD=path/to/record.json' >&2; exit 2; }
	python3 scripts/validate_controlled_drill.py "$(RECORD)"

policy-test:
	python3 scripts/validate_slo_policy.py
	python3 -m unittest tests.test_slo_policy -v

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
	@set -e; for path in $(NATIVE_KUSTOMIZATIONS) "$(NATIVE_PONG_SOURCE)" "$(NATIVE_SITE_SOURCE)"; do \
		if [ ! -f "$$path/kustomization.yaml" ]; then \
			echo "Required live production kustomization is absent: $$path/kustomization.yaml" >&2; \
			exit 1; \
		fi; \
	done
	python3 belacca-gitops/scripts/validate-catalog.py
	python3 belacca-gitops/scripts/validate-recovery-contract.py
	python3 belacca-gitops/scripts/validate-observability.py
	python3 belacca-gitops/scripts/extract-prometheus-config.py
	@rm -f /tmp/belacca-platform-live-*.yaml
	@set -e; for path in $(NATIVE_KUSTOMIZATIONS) "$(NATIVE_PONG_SOURCE)" "$(NATIVE_SITE_SOURCE)"; do \
		name=$$(printf '%s' "$$path" | tr '/.' '__'); \
		kubectl kustomize "$$path" >"/tmp/belacca-platform-live-$$name.yaml"; \
		test -s "/tmp/belacca-platform-live-$$name.yaml"; \
		echo "rendered live production $$path"; \
	done
	@echo 'Rendered every live production Kustomization (native root, Flux children, applications, and routing):'
	@wc -l /tmp/belacca-platform-live-*.yaml

# Compatibility check for callers that specifically validate the native edge.
# The native production root is rendered here as well; this target never falls
# back to another production tree or silently skips a missing native edge.
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

validate: evidence-test drill-test policy-test site-test status-test pong-test manifests
	git diff --check
	@echo 'Workspace validation passed.'
