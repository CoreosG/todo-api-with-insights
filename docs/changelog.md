   # Changelog

   All notable changes to this project will be documented in this file.

   The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
   and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

   ## [Unreleased]

   ### Added
   - ADR-004: API Framework Selection (FastAPI for serverless integration).
   - ADR-005: ETL Method (Hybrid Lambda/Glue pipeline for data lake).
   - ADR-006: Monitoring and Observability (CloudWatch for API/ETL metrics and dashboard).

   ### Changed
   - Updated System_architecture.md Mermaid diagram to include CloudWatch Metrics integration for ETL observability (added arrows from Glue Catalog and Athena to CloudWatch for better alignment with ADR-006).
   - Enhanced System_architecture.md with additional metrics links: Firehose, DynamoDB, Streams, Lambda Sync, and Lambda Async to CloudWatch Metrics for complete API and ETL observability.
   - Refined ADR prompts in `.cursor/prompts/` for better AI-assisted documentation.

   ### Fixed
   - None yet.

   ### Deprecated
   - None yet.

   ### Removed
   - None yet.

   ### Security
   - None yet.

   ## [1.0.0] - 2025-10-15
   - Initial project setup with ADRs 000-006 completed.
   - Architecture diagram established.

   ---

   For older changes, see git history or release notes.
   ```

### 3. **How to Maintain It**
   - **Updates**: Add to "Unreleased" for ongoing changes. When releasing, move to a versioned section (e.g., ## [1.1.0]).
   - **Ties to Commits**: Link to conventional commit messages (e.g., `docs(adr): add ADR-006 monitoring`).
   - **Expansion**: As you add more (e.g., API code or IaC), categorize accordingly.

   This gives you a solid starting point—feel free to tweak based on your exact changes! If you need more entries or help with future updates, let me know.