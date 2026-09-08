apiVersion: ${API_VERSION}
kind: Service
metadata:
${METADATA}
spec:
  type: ${SERVICE_TYPE}
  selector:
${SELECTOR}
  ports:
${PORTS}
