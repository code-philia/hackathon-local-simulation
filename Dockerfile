ARG ARCBENCH_RUNNER_IMAGE=arcbench-runner:local-base
FROM ${ARCBENCH_RUNNER_IMAGE}

LABEL org.opencontainers.image.title="ARC-Bench local submission runner"
LABEL org.opencontainers.image.description="Local wrapper around the exact ARC-Bench production runner image"

COPY local_runner.py /opt/arcbench/local_runner.py

WORKDIR /workspace
CMD ["python3", "/opt/arcbench/local_runner.py"]
