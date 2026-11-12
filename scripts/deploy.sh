#!/usr/bin/env bash
# Deploy ACEest Fitness to Kubernetes using one of several release strategies.
#
#   scripts/deploy.sh init                      apply namespace + all strategy manifests
#   scripts/deploy.sh rolling   <version>       rolling update (auto-undo on failure)
#   scripts/deploy.sh bluegreen <version>       deploy to idle colour, smoke test, switch
#   scripts/deploy.sh canary    <version> [pct] send pct% (default 20) to the new version
#   scripts/deploy.sh promote-canary            make the canary version the stable one
#   scripts/deploy.sh ab        <version>       deploy variant B (header X-User-Group: B)
#   scripts/deploy.sh shadow    <version>       mirror live traffic to the new version
#   scripts/deploy.sh all       <version>       run every strategy with <version>
#
# Environment: IMAGE_REPO (default dhevishreeds/aceest-fitness), NAMESPACE (default aceest),
#              ROLLOUT_TIMEOUT (default 120s).
set -euo pipefail

IMAGE_REPO="${IMAGE_REPO:-dhevishreeds/aceest-fitness}"
NS="${NAMESPACE:-aceest}"
TIMEOUT="${ROLLOUT_TIMEOUT:-120s}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K="kubectl -n ${NS}"
SCRIPTS="$(dirname "$0")"

log() { echo "[deploy] $*"; }

# Smoke test from inside a pod of the given deployment against a service URL.
smoke_test() {
  local deploy="$1" url="$2"
  ${K} exec "deploy/${deploy}" -- python -c \
    "import urllib.request,sys; r=urllib.request.urlopen('${url}/health', timeout=5); sys.exit(r.status!=200)"
}

set_image_and_wait() {
  local deploy="$1" version="$2"
  ${K} set image "deployment/${deploy}" "aceest-fitness=${IMAGE_REPO}:${version}"
  ${K} annotate "deployment/${deploy}" kubernetes.io/change-cause="deploy ${version}" --overwrite
  if ! ${K} rollout status "deployment/${deploy}" --timeout="${TIMEOUT}"; then
    mark_failed "${deploy}"
    return 1
  fi
}

# Label the ReplicaSet of the current (unhealthy) revision so rollbacks skip it.
mark_failed() {
  local deploy="$1" rev
  rev="$(${K} get "deployment/${deploy}" -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')"
  ${K} get rs -l "app=aceest-fitness" -o name | while read -r rs; do
    if [ "$(${K} get "${rs}" -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')" = "${rev}" ] \
       && [ "$(${K} get "${rs}" -o jsonpath='{.metadata.ownerReferences[0].name}')" = "${deploy}" ]; then
      ${K} label "${rs}" aceest/failed=true --overwrite
    fi
  done
}

init() {
  kubectl apply -f "${ROOT}/k8s/namespace.yaml"
  kubectl apply -R -f "${ROOT}/k8s/"
}

rolling() {
  local version="$1"
  log "Rolling update to ${version}"
  if ! set_image_and_wait aceest-rolling "${version}"; then
    log "Rollout failed - rolling back"
    "${SCRIPTS}/rollback.sh" rolling
    return 1
  fi
}

bluegreen() {
  local version="$1" live idle
  live="$(${K} get svc aceest-bluegreen -o jsonpath='{.spec.selector.track}')"
  idle=$([ "${live}" = "blue" ] && echo green || echo blue)
  log "Live=${live}; deploying ${version} to idle=${idle}"
  set_image_and_wait "aceest-${idle}" "${version}"
  ${K} patch svc aceest-bluegreen-preview -p "{\"spec\":{\"selector\":{\"track\":\"${idle}\"}}}"
  if ! smoke_test "aceest-${idle}" "http://aceest-bluegreen-preview"; then
    log "Smoke test failed on ${idle}; live traffic stays on ${live}"
    return 1
  fi
  "${SCRIPTS}/rollback.sh" bluegreen-switch "${idle}"
}

canary() {
  local version="$1" weight="${2:-20}"
  log "Canary ${version} at ${weight}%"
  if ! set_image_and_wait aceest-canary "${version}"; then
    "${SCRIPTS}/rollback.sh" canary
    return 1
  fi
  ${K} annotate ingress aceest-canary nginx.ingress.kubernetes.io/canary-weight="${weight}" --overwrite
}

promote_canary() {
  local image
  image="$(${K} get deploy aceest-canary -o jsonpath='{.spec.template.spec.containers[0].image}')"
  log "Promoting canary image ${image} to stable"
  set_image_and_wait aceest-canary-stable "${image##*:}"
  ${K} annotate ingress aceest-canary nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
}

ab() {
  local version="$1"
  log "A/B: variant B -> ${version}"
  set_image_and_wait aceest-ab-b "${version}"
  ${K} annotate ingress aceest-ab-b --overwrite \
    nginx.ingress.kubernetes.io/canary="true" \
    nginx.ingress.kubernetes.io/canary-by-header="X-User-Group" \
    nginx.ingress.kubernetes.io/canary-by-header-value="B" \
    nginx.ingress.kubernetes.io/canary-by-cookie="ab_group"
}

shadow() {
  local version="$1"
  log "Shadow: mirroring live traffic to ${version}"
  set_image_and_wait aceest-shadow "${version}"
  ${K} annotate ingress aceest-shadow-primary --overwrite \
    "nginx.ingress.kubernetes.io/mirror-target=http://aceest-shadow.${NS}.svc.cluster.local\$request_uri"
}

cmd="${1:-}"; shift || true
case "${cmd}" in
  init) init ;;
  rolling) rolling "$1" ;;
  bluegreen) bluegreen "$1" ;;
  canary) canary "$1" "${2:-20}" ;;
  promote-canary) promote_canary ;;
  ab) ab "$1" ;;
  shadow) shadow "$1" ;;
  all) rolling "$1"; bluegreen "$1"; canary "$1"; ab "$1"; shadow "$1" ;;
  *) sed -n '2,15p' "$0"; exit 1 ;;
esac
