apiVersion: ${API_VERSION}
kind: NetworkPolicy
metadata:
${METADATA}
spec:
  podSelector:
${POD_SELECTOR}
  policyTypes:
${POLICY_TYPES}
${INGRESS_BLOCK}
