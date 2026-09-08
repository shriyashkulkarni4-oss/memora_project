apiVersion: ${API_VERSION}
kind: Ingress
metadata:
${METADATA}
spec:
  ingressClassName: ${INGRESS_CLASS}
  tls:
${TLS}
  rules:
${RULES}
