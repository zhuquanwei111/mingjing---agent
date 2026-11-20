# Use one real verification entry point locally and in CI, following the
# OpenAI Agents SDK team's published maintenance workflow:
# https://developers.openai.com/blog/skills-agents-sdk
# Reference: openai/openai-agents-python at
# 91fb508a8931016efa793b033147d08cd20308cf (Makefile and code-change-verification).
# The commands below use Mingjing's existing checks, not the SDK's test stack.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

P1_DIR := p1-walking-skeleton
PYTHON ?= python3
EXPECTED_RUN_ID ?=
export EXPECTED_RUN_ID

.PHONY: help check smoke acceptance cleanup

help:
	@printf '%s\n' \
	  'make check       Check Python/shell syntax and source whitespace.' \
	  'make smoke       Run the existing macOS smoke test (prepared local environment).' \
	  'make acceptance  Run isolated Linux ARM64/AMD64 acceptance and recovery, then clean up.' \
	  'make cleanup     Remove only the current isolated P1 project and its credentials.'

# Compare tracked source against the empty tree so a clean CI checkout is checked
# too. Check untracked source separately so new local files are not missed.
check:
	git diff --check "$$(git hash-object -t tree /dev/null)" -- '*.py' '*.sh' Makefile '.github/workflows/*.yml' '.github/workflows/*.yaml'
	@set -euo pipefail; while IFS= read -r -d '' file; do \
	  status=0; \
	  output="$$(git diff --no-index --check /dev/null "$$file" 2>&1)" || status=$$?; \
	  if [[ -n "$$output" || "$$status" -gt 1 ]]; then \
	    printf '%s\n' "$$output" >&2; exit 1; \
	  fi; \
	done < <(git ls-files -z --others --exclude-standard -- '*.py' '*.sh' Makefile '.github/workflows/*.yml' '.github/workflows/*.yaml')
	$(PYTHON) -c 'import ast, os, pathlib, subprocess; names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py"]); files = [pathlib.Path(os.fsdecode(name)) for name in names.split(b"\0") if name]; files = [path for path in files if path.is_file()]; [ast.parse(path.read_bytes(), filename=str(path)) for path in files]; print(f"Python syntax passed: {len(files)} files")'
	@set -euo pipefail; while IFS= read -r -d '' script; do \
	  [[ -f "$$script" ]] || continue; \
	  case "$$(head -n 1 "$$script")" in \
	    *bash*) bash -n "$$script" ;; \
	    *) sh -n "$$script" ;; \
	  esac; \
	done < <(git ls-files -z --cached --others --exclude-standard -- '*.sh')
	@printf '%s\n' 'Shell syntax and source whitespace passed. No lint or type-check gate is configured.'

smoke:
	@test -x "$(P1_DIR)/.venv/bin/python" -a -x "$(P1_DIR)/.p1/bin/temporal" || { \
	  printf '%s\n' 'Prepare the macOS environment in p1-walking-skeleton/README.md first.' >&2; exit 1; \
	}
	bash "$(P1_DIR)/infra/smoke.sh"

# new-run.sh refuses an existing runtime.env. Install the cleanup trap only after
# this invocation created its own run, so an existing run is never taken over.
acceptance:
	@case "$$(uname -s)/$$(uname -m)" in \
	  Linux/aarch64|Linux/x86_64) ;; \
	  *) printf '%s\n' 'Acceptance requires an isolated Linux ARM64/AMD64 host with Docker Compose.' >&2; exit 1 ;; \
	esac
	@set -euo pipefail; cd "$(P1_DIR)"; \
	sh infra/new-run.sh; \
	run_id="$$(sed -n 's/^MINGJING_RUN_ID=//p' .p1/runtime.env)"; \
	finish() { \
	  status=$$?; \
	  trap - EXIT; \
	  if ! make --no-print-directory -C "$(CURDIR)" cleanup EXPECTED_RUN_ID="$$run_id"; then \
	    [[ "$$status" -ne 0 ]] || status=1; \
	  fi; \
	  exit "$$status"; \
	}; \
	trap finish EXIT; \
	trap 'exit 130' INT; \
	trap 'exit 143' TERM; \
	sh infra/accept.sh; \
	sh infra/verify-backup.sh; \
	sh infra/verify-temporal-restart.sh; \
	sh infra/verify-rebuild.sh

# Never use docker prune or delete unrelated projects. Keep test evidence local;
# delete generated credentials only after this project's containers/volumes stop.
cleanup:
	@set -euo pipefail; cd "$(P1_DIR)"; \
	if [[ ! -f .p1/runtime.env ]]; then \
	  if [[ -n "$${EXPECTED_RUN_ID:-}" ]]; then \
	    printf '%s\n' 'Missing runtime.env for the run that requires cleanup.' >&2; exit 1; \
	  fi; \
	  printf '%s\n' 'No current isolated P1 run to clean.'; exit 0; \
	fi; \
	run_id="$$(sed -n 's/^MINGJING_RUN_ID=//p' .p1/runtime.env)"; \
	if [[ -n "$${EXPECTED_RUN_ID:-}" && "$$run_id" != "$$EXPECTED_RUN_ID" ]]; then \
	  printf '%s\n' 'Run ID changed; refusing to clean a different isolated project.' >&2; exit 1; \
	fi; \
	sh infra/compose.sh down --volumes --remove-orphans; \
	rm .p1/runtime.env
