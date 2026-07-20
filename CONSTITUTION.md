# AICOS Constitution

## Purpose and Authority

This Constitution defines the non-negotiable engineering principles of AICOS. It governs architecture, implementation, review, testing, operations, and documentation. Contributions that conflict with these principles must be redesigned before acceptance.

## 1. Local-First Architecture

AICOS must be designed to run locally by default. Core functionality, user data, configuration, and essential workflows must remain usable without a network connection or third-party service. Remote capabilities may enhance the product, but must not become an unannounced requirement for core use.

## 2. Free and Open Source by Default

AICOS must favor free and open-source software, open standards, and portable formats. Dependencies with restrictive licensing, opaque lock-in, or avoidable recurring cost require explicit, documented justification. The project must remain practical for individuals and small teams to self-host and extend.

## 3. Cloud Services Are Optional

Cloud services, hosted models, and managed infrastructure are optional integrations. They must be replaceable, configurable, and clearly separated from local operation. No cloud provider may be assumed in domain logic or required for a default installation.

## 4. Single Responsibility for Every Agent

Each agent must have one clearly defined responsibility, a bounded interface, and a documented input/output contract. An agent must not silently absorb unrelated orchestration, persistence, policy, or presentation concerns.

## 5. Event-Driven Communication

Agents and components must communicate through explicit events, commands, or well-defined message contracts. Direct agent-to-agent calls are prohibited. This preserves decoupling, observability, retry behavior, and independent evolution of components.

## 6. Plugin-Based Architecture

Extensible capabilities must be introduced through stable plugin interfaces rather than core modifications for every integration. Plugins must declare their capabilities, configuration, dependencies, and lifecycle requirements. The core must remain usable when optional plugins are absent.

## 7. All LLM Access Through the Model Router

Every interaction with a language model must pass through the Model Router. The router is the sole boundary for provider selection, model routing, credentials, policy enforcement, telemetry, fallback behavior, and cost or usage controls. Components must not call model-provider SDKs directly.

## 8. No Hardcoded Models or Secrets

Model identifiers, provider choices, endpoints, limits, and credentials must never be hardcoded in application logic. API keys and other secrets must never be committed, logged, or embedded in artifacts. Use documented configuration and secret-management mechanisms with safe local defaults.

## 9. Configuration Over Code

Behavior expected to vary by deployment, user, provider, model, or environment must be configurable. Configuration must be validated, documented, versioned where appropriate, and separated from business logic. Defaults must be conservative, transparent, and safe.

## 10. Every Feature Must Be Testable

Every feature must be designed with verifiable behavior and automated tests appropriate to its risk and scope. Business rules must be testable without requiring live cloud services or real model calls. Integration boundaries must support fakes, fixtures, or controlled test environments.

## 11. Structured Logging and Observability

Operational events must use structured, machine-readable logging with useful context such as correlation identifiers, component names, event types, and outcomes. Logs must support diagnosis without exposing secrets, private user data, prompts, or sensitive model outputs.

## 12. Security and Privacy by Default

Security and privacy are default design constraints, not optional features. Apply least privilege, secure defaults, explicit consent for external data transfer, input validation, dependency hygiene, and data minimization. Data must remain local unless a user deliberately enables a documented external integration.

## 13. Documentation Is Part of Delivery

Every major component, plugin, event contract, configuration surface, and external integration must have maintained documentation. Documentation must explain its purpose, boundaries, setup, configuration, failure modes, and testing approach. A major component is not complete until its documentation is reviewed alongside its implementation.

## 14. Clean Architecture and SOLID

AICOS must follow Clean Architecture and SOLID principles. Domain logic must remain independent of frameworks, transport, storage, providers, and user interfaces. Dependencies must point inward toward stable abstractions; infrastructure concerns must implement those abstractions at the boundary. Implementations must favor small, cohesive modules, clear interfaces, and substitutable dependencies.

## Governance

Architecture and code reviews must evaluate changes against this Constitution. When a proposed change appears to conflict with a principle, the contributor must document the conflict and redesign the change. Exceptions are permitted only when they are temporary, narrowly scoped, security-reviewed, documented, and approved by project maintainers with a removal plan.

This Constitution is a living governing document. Amendments require a clear rationale, maintainer review, and an explicit update to this file.
