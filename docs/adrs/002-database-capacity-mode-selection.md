## ADR-002: Capacity Mode Selection

**Date:** 2025-10-14

**Status:** Accepted

***

## Context and Problem Statement

ADR-001 selected **DynamoDB** as the persistent data store. DynamoDB offers two billing and scaling models: **Provisioned Capacity** and **On-Demand Capacity**. A decision is required on which mode best aligns with the "Serverless-first," "Scalability," and "Production-minded" requirements of the system.

## Decision Drivers

* **Serverless Alignment:** Must integrate seamlessly with Lambda/API Gateway and require minimal management.
* **Elastic Scalability:** Must handle unpredictable load and scale automatically from zero.
* **Cost Optimization:** Must optimize for low-to-moderate, potentially bursty traffic patterns typical of a new API.

## Considered Options

* Option A - **On-Demand Capacity Mode** (Pay-per-request)
* Option B - **Provisioned Capacity Mode** (Pay-per-hour for fixed capacity)

## Decision Outcome

**Chosen option:** **On-Demand Capacity Mode**

### Rationale

* **Optimal Serverless Integration:** On-Demand mode is inherently serverless, requiring zero capacity management, monitoring, or auto-scaling configuration. This maximizes developer velocity and aligns perfectly with the architecture's core principle.
* **True Elasticity:** Provides immediate, fully automatic scaling up and down to match actual request volume without throttling. This is crucial for the "production-minded" requirement, ensuring API health under any load.
* **Cost Efficiency for Unpredictable Loads:** Billing is based purely on the actual requests consumed. For a minimal To-Do application with low or sporadic traffic, this avoids the waste of paying for unused, provisioned capacity units.

### Positive Consequences

* ✅ **Zero Capacity Management:** No need to configure auto-scaling or monitor RCU/WCU utilization limits.
* ✅ **No Throttling:** Traffic bursts are handled automatically, ensuring high API availability.

### Negative Consequences

* ❌ **Sacrifices Free Tier:** The DynamoDB Free Tier's 25 RCU/WCU benefit, which primarily applies to Provisioned Mode, is forfeited for the main read/write traffic.
* ❌ **Higher Cost at Steady High Throughput:** If the workload becomes consistently high and predictable, Provisioned Capacity Mode could eventually offer a lower price point, but this risk is minimal for the initial scope.

***

## Detailed Analysis

### Option A: On-Demand Capacity Mode (Chosen)

**Pros:**
* P1. **Full Automation:** Instant, automatic scaling and simple consumption-based pricing.
* P2. **Guaranteed Throughput:** Eliminates risk of throttling under sudden load spikes.

**Cons:**
* C1. **Free Tier Exclusion:** Cannot utilize the Provisioned Free Tier RCU/WCU limits.

**Evaluation:** **Strong Fit (5/5).** Best option for a production-minded system with unknown traffic patterns, prioritizing robustness and operational simplicity over the minimal savings of the Provisioned Free Tier.

### Option B: Provisioned Capacity Mode

**Pros:**
* P1. **Free Tier Benefit:** Allows utilization of the perpetual 25 RCU/WCU Free Tier capacity.
* P2. **Predictable Pricing:** Offers a stable, fixed hourly cost baseline.

**Cons:**
* C1. **Operational Overhead:** Requires manual configuration of RCU/WCU and implementation of Auto Scaling to match varying load.
* C2. **Throttling Risk:** Risk of application throttling if Auto Scaling reacts too slowly or if the capacity ceiling is hit.

**Evaluation:** **Poor Fit (2/5).** Directly compromises the core "Serverless-first" and "Scalability" drivers by reintroducing capacity management and scaling risk, despite the initial cost benefit.

***

## Links

* [Related ADR-000: Architecture Overview](/docs/adrs/000-architecture-overview.md)
* [Related ADR-001: Database Selection](/docs/adrs/001-database-selection.md)
* [Related ADR-003: Database Modeling approach](/docs/adrs/003-data-modeling-approach.md)