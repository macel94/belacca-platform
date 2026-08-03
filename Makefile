.PHONY: init status update site-test pong-test manifests validate

SHELL := /usr/bin/env bash

init:
	git submodule update --init --recursive

status:
	./scripts/status.sh

update:
	git submodule update --remote --merge
	git add .gitmodules cloudnativepong francesco-belacca-site belacca-gitops
	@echo 'Submodules updated and parent Gitlinks staged; review before committing.'

site-test:
	cd francesco-belacca-site && npm test

pong-test:
	cd cloudnativepong && go test ./...
	cd cloudnativepong && go test -race ./...
	cd cloudnativepong && go vet ./...

manifests:
	kubectl kustomize cloudnativepong/k8s/overlays/server >/tmp/belacca-platform-pong.yaml
	kubectl kustomize francesco-belacca-site/deploy >/tmp/belacca-platform-site.yaml
	kubectl kustomize belacca-gitops/clusters/vmi3474918 >/tmp/belacca-platform-gitops.yaml
	kubectl kustomize belacca-gitops/clusters/vmi3474918/routing >/tmp/belacca-platform-routing.yaml
	@echo 'Rendered manifests:'
	@wc -l /tmp/belacca-platform-{pong,site,gitops,routing}.yaml

validate: site-test pong-test manifests
	git diff --check
	@echo 'Workspace validation passed.'
