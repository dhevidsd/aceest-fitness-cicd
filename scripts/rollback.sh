#!/usr/bin/env bash
# Revert ACEest Fitness to the last stable version for a given strategy.
#
#   scripts/rollback.sh rolling                  kubectl rollout undo
#   scripts/rollback.sh bluegreen                switch live traffic back to the other colour
#   scripts/rollback.sh bluegreen-switch <colour> point live traffic at <colour>
#   scripts/rollback.sh canary                   0% canary traffic + undo canary deployment
#   scripts/rollback.sh ab                       disable variant B routing
#   scripts/rollback.sh shadow                   stop mirroring + undo shadow deployment
#   scripts/rollback.sh all                      roll back every strategy
set -euo pipefail

NS="${NAMESPACE:-aceest}"
TIMEOUT="${ROLLOUT_TIMEOUT:-120s}"
K="kubectl -n ${NS}"

log() { echo "[rollback] $*"; }

# Newest earlier revision that was not marked failed and runs a different image
# than the current one, i.e. the last known-good version.
last_good_revision() {
  ${K} get rs -o json | python3 -c '
import json, sys
deploy = sys.argv[1]
items = [
    rs for rs in json.load(sys.stdin)["items"]
    if any(o["name"] == deploy for o in rs["metadata"].get("ownerReferences", []))
]
def rev(rs):
    return int(rs["metadata"]["annotations"]["deployment.kubernetes.io/revision"])
def image(rs):
    return rs["spec"]["template"]["spec"]["containers"][0]["image"]
current = max(items, key=rev)
for rs in sorted(items, key=rev, reverse=True)[1:]:
    if rs["metadata"].get("labels", {}).get("aceest/failed") != "true" \
            and image(rs) != image(current):
        print(rev(rs))
        break
' "$1"
}

undo() {
  local target
  target="$(last_good_revision "$1")"
  if [ -n "${target}" ]; then
    log "Rolling $1 back to last good revision ${target}"
    ${K} rollout undo "deployment/$1" --to-revision="${target}"
    ${K} annotate "deployment/$1" kubernetes.io/change-cause="rollback to revision ${target}" --overwrite
  else
    ${K} rollout undo "deployment/$1"
  fi
  ${K} rollout status "deployment/$1" --timeout="${TIMEOUT}"
}

switch_colour() {
  local target="$1" other
  other=$([ "${target}" = "blue" ] && echo green || echo blue)
  for svc in aceest-bluegreen aceest-bluegreen-nodeport; do
    ${K} patch svc "${svc}" -p "{\"spec\":{\"selector\":{\"track\":\"${target}\"}}}"
  done
  ${K} patch svc aceest-bluegreen-preview -p "{\"spec\":{\"selector\":{\"track\":\"${other}\"}}}"
  # ingress-nginx needs a few seconds to pick up the new endpoints.
  sleep "${SWITCH_SETTLE_SECONDS:-5}"
  log "Blue-green live colour is now ${target}"
}

cmd="${1:-}"
case "${cmd}" in
  rolling) log "Undoing rolling deployment"; undo aceest-rolling ;;
  bluegreen)
    live="$(${K} get svc aceest-bluegreen -o jsonpath='{.spec.selector.track}')"
    switch_colour "$([ "${live}" = "blue" ] && echo green || echo blue)" ;;
  bluegreen-switch) switch_colour "$2" ;;
  canary)
    ${K} annotate ingress aceest-canary nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
    undo aceest-canary || true ;;
  ab)
    # Removing the routing rules sends every user back to variant A.
    ${K} annotate ingress aceest-ab-b nginx.ingress.kubernetes.io/canary-by-header- \
      nginx.ingress.kubernetes.io/canary-by-header-value- nginx.ingress.kubernetes.io/canary-by-cookie- ;;
  shadow)
    ${K} annotate ingress aceest-shadow-primary nginx.ingress.kubernetes.io/mirror-target- || true
    undo aceest-shadow || true ;;
  all) for s in rolling bluegreen canary ab shadow; do "$0" "$s"; done ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac
