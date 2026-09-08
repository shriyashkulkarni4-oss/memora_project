apiVersion: ${API_VERSION}
kind: Deployment
metadata:
${METADATA}
spec:
  replicas: ${REPLICAS}
  selector:
${SELECTOR}
  template:
${POD_TEMPLATE}
