apiVersion: ${API_VERSION}
kind: StatefulSet
metadata:
${METADATA}
spec:
  serviceName: ${SERVICE_NAME}
  replicas: ${REPLICAS}
  selector:
${SELECTOR}
  template:
${POD_TEMPLATE}
  volumeClaimTemplates:
${VOLUME_CLAIMS}
