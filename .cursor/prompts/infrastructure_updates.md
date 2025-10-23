# Prompts

prompt:

Note: this has context from etl_stack_implementation.md prompt, this prompt was used to ensure IaC was correct for this stack.

go to /infra, activate venv-infra and run cdk synth. use aws mcp servers for refference when needed. ensure everything is connected seamlessly and applying proper @adrs/ rules (like ensure least permissions, resource tagging, all monitoring tools/resources are implemented)


run cdk deploy TodoEtlStack --require-approval never and fix errors
run cdk deploy TodoMonitoringStack --require-approval never and fix errors


Objective:
Update Infrastructure as Code to integrate ETL and Monitoring stacks seamlessly with existing API and Data stacks, ensuring:
- Proper CDK stack dependencies and resource sharing
- IAM roles and policies with least privilege access
- Resource tagging for cost tracking and management
- Error handling and deployment validation

## Commit Link
23b7a1bc3ba9d958caebc3a30f763788b1e6d654 (same as monitoring_stack_implementation.md, both share this commit, i asked for monitoring stack first and then to check, agent updated the same files)
