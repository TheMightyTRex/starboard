#!/usr/bin/env bash
# Runs the privacy check before every commit in this clone.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
cat > .git/hooks/pre-commit <<'HOOK'
#!/usr/bin/env bash
exec tools/check-private.sh --staged
HOOK
chmod +x .git/hooks/pre-commit
echo "Pre-commit privacy check installed."
