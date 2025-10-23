
# Prompts

Prompt:

implement @next-steps.md , update as you go, you can stop implementing to ask questions if you need. make use of mcp servers, me, current codebase.

on etl folder we have a venv-etl, activate it, create requirements.txt and requirements-dev.txt, setup linting (black, ruff, mypy), make linting pass, create unit tests. create runbook on a new folder named ETL. Update @DEPLOYMENT_AND_TESTING.md at the end with new info.

go to /infra, activate venv-infra and run cdk synth. use aws mcp servers for refference when needed. ensure everything is connected seamlessly and applying proper @adrs/ rules

run cdk deploy TodoEtlStack --require-approval never and fix errors

make a script to test ETL in @scripts/ , you can reutilize @test-api.ps1 logic to create 3 users and spam create and update tasks, @task_controller.py for refference

Test deploy, view resource logs for errors, iterate untill success, final objective:
- Check if gold layer has files that make sense (actual metrics)


Objective:
Implement a complete ETL pipeline with Bronze/Silver/Gold data lake architecture, including:
- DynamoDB Streams CDC processing with Lambda
- Kinesis Firehose for data ingestion
- Glue jobs for data transformation and analytics
- Athena integration for querying
- Comprehensive testing and documentation
- CloudWatch monitoring and dashboards



Note: next-steps.md became implementation_report.md on root dir when challenge ended.

## Commit Link
1f040ec8a91898994ef15e8db1ca353b4a4e619a
